""" Direct submission of data to ABRP. """
from time import time, sleep
from threading import Thread, Condition
import json
import logging
import requests

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
        self._car_model = car.get_abrp_model()
        self._config = config
        self._api_key = config['api_key']
        self._token = config['token']
        self._poll_interval = config['interval']
        self._running = False
        self._thread = None
        self._data_queue = []
        self._data_queue_lock = Condition()

    def start(self):
        """ Start the submission thread """
        self._running = True
        self._thread = Thread(target=self.submit_data, name="EVNotiPi/ABRP")
        self._thread.start()
        self._car.register_data(self.data_callback)

    def stop(self):
        """ Stop the submission thread """
        self._car.unregister_data(self.data_callback)
        self._running = False
        with self._data_queue_lock:
            self._data_queue_lock.notify()
        self._thread.join()

    def data_callback(self, data):
        """ Callback to get new data from "car" """
        self._log.debug("Enqeue...")
        with self._data_queue_lock:
            if data['SOC_DISPLAY'] is not None:
                self._data_queue.append(data)
                self._data_queue_lock.notify()

    def submit_data(self):
        """ Data submission thread """

        session = requests.Session()
        while self._running:
            now = time()

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

            with self._data_queue_lock:
                self._log.debug('Waiting...')
                self._data_queue_lock.wait()
                if len(self._data_queue) == 0:
                    continue

                new_data = self._data_queue.copy()
                self._data_queue.clear()

            for data in new_data:
                for key, values in avgs.items():
                    if key in data and data[key] is not None:
                        values.append(data[key])

            data = new_data[-1]

            payload = {
                'car_model': self._car_model,
                'utc':       data['timestamp'],
            }
            payload.update({v[0]: round(data[k], v[1]) for k, v in PID_MAP.items()
                            if k in data and data[k] is not None})

            # Apply averages
            payload.update({PID_MAP[k][0]: round(
                sum(v)/len(v), PID_MAP[k][1]) for k, v in avgs.items() if len(v) > 0})

            if 'speed' in payload and 'lon' in payload and 'lat' in payload:
                payload['speed'] *= 3.6      # convert from m/s to km/h
            else:
                # Skip iteration, ABRP does not accept payload without location fields
                self._log.debug("location missing, skip... %s", payload)
                continue

            self._log.debug("Transmit...")

            try:
                payload_str = json.dumps(payload)
                ret = session.post(API_URL + "/send",
                                   data={'api_key': self._api_key,
                                         'token': self._token,
                                         'tlm': payload_str})
                self._log.debug("Post result: %i %s",
                                ret.status_code, ret.text)

                if ret.status_code != requests.codes.ok or ret.json()['status'] != "ok":
                    self._log.error("Submit error: %s %s %s",
                                    payload_str, str(ret), ret.text)

            except requests.exceptions.ConnectionError as err:
                self._log.error("ConnectionError: %s", err)
            except SubmitError as err:
                self._log.error("SubmitError: %s", err)

            # Prime next loop iteration
            if self._running:
                interval = self._poll_interval - (time() - now)
                sleep(max(0, interval))

    def check_thread(self):
        """ Return the status of the thread """
        return self._thread.is_alive()
