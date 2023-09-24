""" Direct submission of data to ABRP. """
from asyncio import create_task
from time import monotonic
import json
import logging
import aiohttp

PID_MAP = {
    'SOC_DISPLAY':      ['soc', 1],                 # %
    'dcBatteryPower':   ['power', 2],               # kW
    'speed':            ['speed', 1],               # km/h
    'latitude':         ['lat', 9],                 # °
    'longitude':        ['lon', 9],                 # °
    'charging':         ['is_charging', 0],         # bool 1/0
    'rapidChargePort':  ['is_dcfc', 0],             # bool 1/0
    'isParked':         ['is_parked', 0],           # bool 1/0
    'cumulativeEnergyCharged': ['kwh_charged', 2],  # kWh
    'soh':              ['soh', 1],                 # %
    'heading':          ['heading', 2],             # °
    'altitude':         ['elevation', 1],           # m
    'externalTemperature':   ['ext_temp', 1],       # °C
    'batteryAvgTemperature': ['batt_temp', 1],      # °C
    'dcBatteryVoltage': ['voltage', 2],             # V
    'dcBatteryCurrent': ['current', 2],             # A
    'odo':              ['odometer', 2],            # km
}

API_URL = "https://api.iternio.com/1/tlm"


class SubmitError(Exception):
    """ Problem while submitting data. """


class ABRP:
    """ The ABRP class """
    def __init__(self, config, car):
        self._log = logging.getLogger("EVNotiPi/ABRP")
        self._log.info("Initializing ABRP")

        self._car = car
        self._config = config
        self._api_key = config['api_key']
        self._token = config['token']
        self._poll_interval = config['interval']
        self._running = False
        self._task = None
        self._data_queue = []
        self._session = aiohttp.ClientSession()
        self._next_transmit = 0

    def start(self):
        """ Start the submission thread """
        assert self._running is False
        self._running = True
        self._car.register_data(self.data_callback)

    def stop(self):
        """ Stop the submission thread """
        assert self._running is True
        self._car.unregister_data(self.data_callback)
        self._running = False
        with self._data_queue_lock:
            self._data_queue_lock.notify()
        self._task.join()

    async def data_callback(self, data):
        """ Callback to get new data from "car" """
        self._log.debug("Enqeue...")
        # ABRP requires speed and timestamp, ignore data if missing
        if data['SOC_DISPLAY'] is not None \
                and 'timestamp' in data and data['timestamp'] is not None \
                and 'speed' in data and data['speed'] is not None:
            self._data_queue.append(data)

        if self._task is None or self._task.done():
            self._task = create_task(self.submit_data())

    async def submit_data(self):
        """ Data submission """
        session = self._session
        now = monotonic()
        log = self._log

        if now >= self._next_transmit and len(self._data_queue) > 0:
            avgs = {
                'dcBatteryCurrent': [],
                'dcBatteryPower': [],
                'dcBatteryVoltage': [],
                'speed': [],
                'latitude': [],
                'longitude': [],
                'heading': [],
                'altitude': [],
            }

            for data in self._data_queue:
                for key, values in avgs.items():
                    if key in data and data[key] is not None:
                        values.append(data[key])

            data = self._data_queue[-1]
            self._data_queue.clear()

            payload = {
                'utc':       int(data['timestamp']),
                'power':     0,
                'current':   0,
            }
            payload.update({v[0]: round(data[k], v[1]) for k, v in PID_MAP.items()
                            if k in data and data[k] is not None})

            # Apply averages
            payload.update({PID_MAP[k][0]: round(
                sum(v)/len(v), PID_MAP[k][1]) for k, v in avgs.items() if len(v) > 0})

            payload['speed'] *= 3.6      # convert from m/s to km/h

            if 'capacity' in payload:
                payload['capacity'] /= 1000  # Wh -> kWh

            log.debug("Transmit...")

            try:
                log.debug("Send payload %s", payload)
                payload_str = json.dumps(payload)
                ret = await session.post(API_URL + "/send",
                                         json={'api_key': self._api_key,
                                               'token': self._token,
                                               'tlm': payload_str})
                if ret.status_code != 200 or ret.json()['status'] != "ok":
                    log.error("Submit error: %s %s %s",
                              payload_str, str(ret), ret.text)
                else:
                    log.debug("Post result: %i %s",
                              ret.status_code, ret.text)

            except aiohttp.ClientConnectionError as err:
                log.error("ConnectionError: %s", err)

            self._next_transmit = now + self._poll_interval

    def check_thread(self):
        """ Return the status of the thread """
        return self._running
