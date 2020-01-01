from time import time, sleep
from threading import Thread
from dongle import NoData, CanError
import logging

def ifbu(in_bytes): return int.from_bytes(in_bytes, byteorder='big', signed=False)
def ifbs(in_bytes): return int.from_bytes(in_bytes, byteorder='big', signed=True)
def ffbu(in_bytes): return float(int.from_bytes(in_bytes, byteorder='big', signed=False))
def ffbs(in_bytes): return float(int.from_bytes(in_bytes, byteorder='big', signed=True))

class DataError(Exception): pass

class Car:
    def __init__(self, config, dongle, gps):
        self.log = logging.getLogger("EVNotiPi/Car")
        self.config = config
        self.dongle = dongle
        self.gps = gps
        self.poll_interval = config['interval']
        self.thread = None
        self.skip_polling = False
        self.running = False
        self.last_data = 0
        self.watchdog = time()
        self.watchdog_timeout = self.poll_interval * 10 if self.poll_interval else 10
        self.data_callbacks = []

    def start(self):
        self.running = True
        self.thread = Thread(target = self.pollData, name = "EVNotiPi/Car")
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()

    def pollData(self):
        while self.running:
            now = time()
            self.watchdog = now

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
                    # Location:
                    'latitude':     None,
                    'longitude':    None,
                    'speed':        None,
                    'fix_mode':     None,
                    }
            if not self.skip_polling or self.dongle.isCarAvailable():
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
                    if not self.dongle.isCarAvailable():
                        self.log.info("Car off detected. Stop polling until car on.")
                        self.skip_polling = True
                    sleep(1)

            fix = self.gps.fix()
            if fix and fix.mode > 1:
                if data['charging'] or data['normalChargePort'] or data['rapidChargePort']:
                    speed = 0.0
                elif isnan(speed):
                    speed = None
                else:
                    speed = float(fix.speed)

                data.update({
                    'fix_mode':     fix.mode,
                    'latitude':     float(fix.latitude),
                    'longitude':    float(fix.longitude),
                    'speed':        speed
                    'gdop':         float(fix.gdop),
                    'pdop':         float(fix.pdop),
                    'hdop':         float(fix.hdop),
                    'vdop':         float(fix.vdop),
                    'altitude':     float(fix.altitude) fix.mode > 2 and not isnan(fix.altitude) else None,
                    'gps_device':   fix.device if fix.device else None,
                    })

            if self.dongle.watchdog:
                thresholds = self.dongle.watchdog.getThresholds()
                volt = self.dongle.getObdVoltage()

                data.update ({
                    'obdVoltage':               volt,
                    'startupThreshold':         thresholds['startup'],
                    'shutdownThreshold':        thresholds['shutdown'],
                    'emergencyThreshold':       thresholds['emergency'],
                    })

            if data:
                for cb in self.data_callbacks:
                    cb(data)

            if self.running:
                if self.poll_interval:
                    runtime = time() - now
                    interval = self.poll_interval - (runtime if runtime > self.poll_interval else 0)
                    if interval > 0:
                        sleep(interval)

                elif self.skip_polling:
                    sleep(1)

    def registerData(self, callback):
        self.data_callbacks.append(callback)

    def unregisterData(self, callback):
        self.data_callbacks.remove(callback)

    def checkWatchdog(self):
        return self.thread.is_alive() # (time() - self.watchdog) <= self.watchdog_timeout
