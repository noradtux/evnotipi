#!/usr/bin/env python3

from time import time, sleep
from threading import Thread, Condition
import json
import logging
import requests

PID_MAP = {
        "dcBatteryCurrent": "current",
        "dcBatteryVoltage": "voltage",
        "dcBatteryPower":   "power",
        "SOC_DISPLAY":      "soc",
        "soh":              "soh",
        "charging":         "is_charging",
        "speed":            "speed",
        "altitude":         "elevation",
        "longitude":        "lon",
        "latitude":         "lat",
        "externalTemperature":   "ext_temp",
        "batteryAvgTemperature": "batt_temp",
        }

API_URL = "https://api.iternio.com/1/tlm"

class SubmitError(Exception): pass

class ABRP:
    def __init__(self, config, car, evnotify):
        self._log = logging.getLogger("EVNotiPi/ABRP")
        self._log.info("Initializing ABRP")

        self._car = car
        self._car_model = car.getABRPModel()
        self._config = config
        self._session = requests.Session()
        self._api_key = config['api_key']
        self._token = config['token']
        self._poll_interval = config['interval']
        self._running = False
        self._thread = None
        self._data = []
        self._data_lock = Condition()

    def start(self):
        self._running = True
        self._thread = Thread(target=self.submitData, name="EVNotiPi/ABRP")
        self._thread.start()
        self._car.registerData(self.dataCallback)

    def stop(self):
        self._car.unregisterData(self.dataCallback)
        self._running = False
        with self._data_lock:
            self._data_lock.notify()
        self._thread.join()

    def dataCallback(self, data):
        self._log.debug("Enqeue...")
        with self._data_lock:
            if data['SOC_DISPLAY'] is not None:
                self._data.append(data)
                self._data_lock.notify()

    def submitData(self):
        while self._running:
            now = time()

            avgs = {
                'dcBatteryCurrent': [],
                'dcBatteryPower': [],
                'dcBatteryVoltage': [],
                'speed': [],
                'latitude': [],
                'longitude': [],
                'altitude': [],
                }
            with self._data_lock:
                self._log.debug('Waiting...')
                self._data_lock.wait()
                if len(self._data) == 0:
                    continue

                for d in self._data:
                    for k, v in avgs.items():
                        if k in d and d[k] is not None:
                            v.append(d[k])

                data = self._data[-1]
                self._data.clear()

            payload = {
                'car_model': self._car_model,
                'utc':       data['timestamp'],
                }
            payload.update({v:data[k] for k, v in PID_MAP.items()
                            if k in data and data[k] is not None})

            # Apply averages
            payload.update({PID_MAP[k]:sum(v)/len(v) for k, v in avgs.items() if len(v) > 0})

            if 'speed' in payload and 'lon' in payload and 'lat' in payload:
                payload['speed'] *= 3.6      # convert from m/s to km/h
            else:
                # Skip interation, ABRP does not accept payload without location fields
                self._log.debug("location missing, skip... %s", payload)
                continue

            self._log.debug("Transmit...")

            try:
                payload_str = json.dumps(payload)
                ret = self._session.post(API_URL + "/send",
                                         data={'api_key': self._api_key,
                                               'token': self._token,
                                               'tlm': payload_str})
                self._log.debug("Post result: %i %s", ret.status_code, ret.json())

                if ret.status_code != requests.codes.ok or ret.json()['status'] != "ok":
                    self._log.error("Submit error: %s %s %s", payload_str, str(ret), ret.text)

                # XXX Need to reimplement, not working well
                #abrpSocThreshold = ABRP.getNextCharge()

            except requests.exceptions.ConnectionError as e:
                self._log.error(e)
            except SubmitError as e:
                self._log.error(e)

            # Prime next loop iteration
            if self._running:
                runtime = time() - now
                interval = self._poll_interval - (runtime if runtime > self._poll_interval else 0)
                sleep(max(0, interval))


    def getNextCharge(self):
        ret = self._session.get("{1}/get_next_charge?api_key={0._api_key}&token={0._token}".format(self, API_URL))
        if ret.status_code == requests.codes.ok and ret.json()['status'] == "ok":
            return ret.json()['next_charge']
        else:
            raise SubmitError(str(ret), ret.text)

    def checkWatchdog(self):
        return self._thread.is_alive()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    import json, sys
    with open('config.json', encoding='utf-8') as config_file:
        config = json.loads(config_file.read())

    from cars.IONIQ_BEV import IONIQ_BEV
    from dongles.FakeDongle import FakeDongle

    dongle = FakeDongle(config['dongle'])
    car = IONIQ_BEV(dongle)

    abrp = ABRP(config['abrp'], car, None, None)

    ret = abrp.getNextCharge()
    print(ret)

    ret = abrp.submit(car.readDongle(),
                      {'latitude':56.0,
                       'longitude':9.0,
                       'speed':11.1,
                       'altitude':9.9})
    print(ret, ret.text)

