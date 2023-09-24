""" The car polling loop and associated infrastructure """
from asyncio import gather, sleep
from time import time, monotonic
import logging
from numpy import percentile, mean
from dongle import NoData, CanError


def ifbu(in_bytes):
    """ int from bytes unsigned """
    return int.from_bytes(in_bytes, byteorder='big', signed=False)


def ifbs(in_bytes):
    """ int from bytes signed """
    return int.from_bytes(in_bytes, byteorder='big', signed=True)


def ffbu(in_bytes):
    """ float from int from bytes unsigned """
    return float(int.from_bytes(in_bytes, byteorder='big', signed=False))


def ffbs(in_bytes):
    """ float from int from bytes signed """
    return float(int.from_bytes(in_bytes, byteorder='big', signed=True))


class DataError(ValueError):
    """ Problem with data occured """


class RollingAverage:
    def __init__(self, length=10):
        self._buf = [0] * length
        self._idx = 0
        self._len = 0

    def push(self, value):
        self._buf[self._idx] = value
        self._idx = (self._idx + 1) % len(self._buf)
        if self._len < len(self._buf):
            self._len += 1

    def get(self, min_len_perc=0):
        assert 0 <= min_len_perc <= 1
        return mean(self._buf[:self._len]) if self._len >= max(1, len(self._buf) * min_len_perc) else None

    def get_perc(self, perc):
        data = self._buf[:self._len]
        cut = percentile(data, [100-perc, perc])
        return mean(data, where=list(
            map(lambda a: cut[0] <= a <= cut[1], data)))


class Car:
    """ Abstract class implementing the car polling loop.
        Subclasses need to implement read_dongle """

    def __init__(self, config, dongle, watchdog, gps):
        self._log = logging.getLogger("EVNotiPi/Car")
        self.id = config['id']
        self._config = config
        self._dongle = dongle
        self._watchdog = watchdog
        self._gps = gps
        self._poll_interval = config['interval']
        self._charge_interval = config['charge_interval'] or config['interval']
        self._task = None
        self._skip_polling = False
        self._next_poll = 0
        self._running = False
        self.last_data = monotonic()
        self._data_callbacks = set()
        self.is_available = watchdog.is_car_available
        self._can_tries = max(1, self._config.get('can_tries', 3))

    async def read_dongle(self, data):
        """ Get data from CAN bus and put it into "data" dictionary """
        raise NotImplementedError()

    def start(self):
        """ Start the poller thread. """
        self._running = True

    def stop(self):
        """ Stop the poller thread. """
        self._running = False

    async def poll_data(self):
        """ The poller thread. """

        log = self._log

        now = monotonic()

        # initialize data with required fields; saves all those checks later
        data = {
            'timestamp':    time(),
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
        if not self._skip_polling or self.is_available():
            if self._skip_polling:
                log.info("Resume polling.")
                self._skip_polling = False

            try:
                await self.read_dongle(data)  # readDongle updates data inplace
                self.last_data = now
            except CanError as err:
                log.warning(err)
                self._next_poll = now + 1
                return
            except NoData:
                log.info("NO DATA")
                self._next_poll = now + 1
                if not self.is_available():
                    log.info("Car off detected. Stop polling until car on.")
                    self._skip_polling = True
                    return

        fix = self._gps.fix()
        if fix and fix['mode'] > 1:
            data.update({
                'fix_mode':     fix['mode'],
                'latitude':     fix['latitude'],
                'longitude':    fix['longitude'],
                'gdop':         fix['gdop'],
                'pdop':         fix['pdop'],
                'hdop':         fix['hdop'],
                'vdop':         fix['vdop'],
                'tdop':         fix['tdop'],
                'altitude':     fix['altitude'],
                'gps_device':   fix['device'],
                'heading':      fix['heading'],
                'gps_speed':    fix['speed'],
            })

        if fix and 'time' in fix and fix['time'] and \
                abs(data['timestamp'] - fix['time']) > 10:
            data['timestamp'] = float(fix['time'])

        if 'realVehicleSpeed' in data:
            data['speed'] = data['realVehicleSpeed']
        elif fix and fix['mode'] > 1:
            data['speed'] = fix['speed']

        if data['charging'] \
                or data['normalChargePort'] \
                or data['rapidChargePort']:
            data['speed'] = 0.0

        if hasattr(self._dongle, 'get_obd_voltage'):
            data.update({
                'obdVoltage':       self._dongle.get_obd_voltage(),
            })
        elif hasattr(self._watchdog, 'get_voltage'):
            data.update({
                'obdVoltage':       self._watchdog.get_voltage(),
            })

        if hasattr(self._watchdog, 'get_thresholds'):
            thresholds = self._watchdog.get_thresholds()

            data.update({
                'startupThreshold':         thresholds['startup'],
                'shutdownThreshold':        thresholds['shutdown'],
                'emergencyThreshold':       thresholds['emergency'],
            })

        await gather(*self._data_callbacks)

        if data['charging']:
            self._next_poll = now + self._charge_interval
        elif self._poll_interval > 0:
            self._next_poll = now + self._poll_interval
        elif self._skip_polling:
            # Limit poll rate if polling shall be skipped
            self._next_poll = now + 1

    def register_data(self, callback):
        """ Register a callback that get called with new data. """
        self._data_callbacks.add(callback)

    def unregister_data(self, callback):
        """ Unregister a callback. """
        self._data_callbacks.remove(callback)

    def check_thread(self):
        """ Return state of thread. """
        return self._running

    async def wait_next_poll(self):
        interval = self._next_poll - monotonic()
        await sleep(max(0, interval))
