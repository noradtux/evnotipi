""" The car polling loop and associaterd infrastructure """

from threading import Thread
from time import time, sleep
import logging
from dongle.dongle import NoData, CanError

def ifbu(in_bytes):
    """ convert bytes to unsigned integer """
    return int.from_bytes(in_bytes, byteorder='big', signed=False)

def ifbs(in_bytes):
    """ convert bytes to signed integer """
    return int.from_bytes(in_bytes, byteorder='big', signed=True)

def ffbu(in_bytes):
    """ convert bytes to float """
    return float(int.from_bytes(in_bytes, byteorder='big', signed=False))

def ffbs(in_bytes):
    """ convert bytes to float """
    return float(int.from_bytes(in_bytes, byteorder='big', signed=True))

class DataError(ValueError):
    """ Something is wrong with data """

class Car:
    """ Abstract class implementing the car polling loop.
        Subclasses need to implement readDongle """

    def __init__(self, config, dongle, watchdog, gps):
        self.log = logging.getLogger("EVNotiPi/Car")
        self.config = config
        self.dongle = dongle
        self.watchdog = watchdog
        self.gps = gps
        self.poll_interval = config['interval']
        self.thread = None
        self.skip_polling = False
        self.running = False
        self.last_data = 0
        self.data_callbacks = []

    def start(self):
        """ start the poller thread """
        self.running = True
        self.thread = Thread(target=self.pollData, name="EVNotiPi/Car")
        self.thread.start()

    def stop(self):
        """ stop the poller thread """
        self.running = False
        self.thread.join()

    def readDongle(self, data):
        """ Get data from CAN bus and put it into "data" dictionary """
        raise NotImplementedError()

    def pollData(self):
        """ The polling thread """
        while self.running:
            now = time()

            # initialize data with required fields; saves all those checks later
            data = {
                'timestamp':    now,
                # Base:
                'SOC_BMS':      None,
                'SOC_DISPLAY':  None,
                # Extended:
                'auxBatteryVoltage':        None,
                'batteryInletTemperature':  None,
                'batteryMaxTemperature':    None,
                'batteryMinTemperature':    None,
                'cumulativeEnergyCharged':  None,
                'cumulativeEnergyDischarged':   None,
                'charging':                 None,
                'normalChargePort':         None,
                'rapidChargePort':          None,
                'dcBatteryCurrent':         None,
                'dcBatteryPower':           None,
                'dcBatteryVoltage':         None,
                'soh':                      None,
                'externalTemperature':      None,
                'odo':                      None,
                # Location:
                'latitude':     None,
                'longitude':    None,
                'speed':        None,
                'fix_mode':     0,
                }
            if not self.skip_polling or self.watchdog.isCarAvailable():
                if self.skip_polling:
                    self.log.info("Resume polling.")
                    self.skip_polling = False
                try:
                    self.readDongle(data)  # readDongle updates data inplace
                    self.last_data = now
                except CanError as e:
                    self.log.warning(e)
                except NoData:
                    self.log.info("NO DATA")
                    if not self.watchdog.isCarAvailable():
                        self.log.info("Car off detected. Stop polling until car on.")
                        self.skip_polling = True
                    sleep(1)

            fix = self.gps.fix()
            if fix and fix['mode'] > 1:
                if data['charging'] or data['normalChargePort'] or data['rapidChargePort']:
                    speed = 0.0
                else:
                    speed = fix['speed']

                data.update({
                    'fix_mode':     fix['mode'],
                    'latitude':     fix['latitude'],
                    'longitude':    fix['longitude'],
                    'speed':        speed,
                    'gdop':         fix['gdop'],
                    'pdop':         fix['pdop'],
                    'hdop':         fix['hdop'],
                    'vdop':         fix['vdop'],
                    'tdop':         fix['tdop'],
                    'altitude':     fix['altitude'],
                    'gps_device':   fix['device'],
                    })

            if hasattr(self.dongle, 'getObdVoltage'):
                data.update({
                    'obdVoltage':       self.dongle.getObdVoltage(),
                    })
            elif hasattr(self.watchdog, 'getVoltage'):
                data.update({
                    'obdVoltage':       self.watchdog.getVoltage(),
                    })

            if hasattr(self.watchdog, 'getThresholds'):
                thresholds = self.watchdog.getThresholds()

                data.update({
                    'startupThreshold':         thresholds['startup'],
                    'shutdownThreshold':        thresholds['shutdown'],
                    'emergencyThreshold':       thresholds['emergency'],
                    })

            for cb in self.data_callbacks:
                cb(data)

            if self.running:
                if self.poll_interval:
                    runtime = time() - now
                    interval = self.poll_interval - (runtime if runtime > self.poll_interval else 0)
                    sleep(max(0, interval))

                elif self.skip_polling or data.get('charging', False):
                    sleep(1)

    def registerData(self, callback):
        """ Register a function to be called when new data is available """
        if callback not in self.data_callbacks:
            self.data_callbacks.append(callback)

    def unregisterData(self, callback):
        """ Unregister a function to be called when new data is available """
        self.data_callbacks.remove(callback)

    def checkWatchdog(self):
        """ Check if polling thread is still alive """
        return self.thread.is_alive()
