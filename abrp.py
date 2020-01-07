#!/usr/bin/env python3

import requests
from time import time, sleep
import json
import logging
from threading import Thread, Condition

PidMap = {
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

ApiUrl = "https://api.iternio.com/1/tlm"

class SubmitError(Exception): pass

class ABRP:
    def __init__(self, config, car, evnotify):
        self.log = logging.getLogger("EVNotiPi/ABRP")
        self.log.info("Initializing ABRP")

        self.car = car
        self.car_model = car.getABRPModel()
        self.config = config
        self.session = requests.Session()
        self.api_key = config['api_key']
        self.token = config['token']
        self.poll_interval = config['interval']
        self.running = False
        self.thread = None
        self.data = []
        self.data_lock = Condition()

    def start(self):
        self.running = True
        self.thread = Thread(target = self.submitData, name = "EVNotiPi/ABRP")
        self.thread.start()
        self.car.registerData(self.dataCallback)

    def stop(self):
        self.car.unregisterData(self.dataCallback)
        self.running = False
        with self.data_lock:
            self.data_lock.notify()
        self.thread.join()

    def dataCallback(self, data):
        self.log.debug("Enqeue...")
        with self.data_lock:
            if data['SOC_DISPLAY'] != None:
                self.data.append(data)
                self.data_lock.notify()

    def submitData(self):
        while self.running:
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
            with self.data_lock:
                self.log.debug('Waiting...')
                self.data_lock.wait()
                if len(self.data) == 0:
                    continue

                for d in self.data:
                    for k,v in avgs.items():
                        if k in d and d[k] != None:
                            v.append(d[k])

                data = self.data[-1]
                self.data.clear()

            payload = {
                    'car_model': self.car_model,
                    'utc':       data['timestamp'],
                    }
            payload.update({v:data[k] for k,v in PidMap.items() if k in data and data[k] != None})

            # Apply averages
            payload.update({PidMap[k]:sum(v)/len(v) for k,v in avgs.items() if len(v) > 0})

            if 'speed' in payload and 'lon' in payload and 'lat' in payload:
                payload['speed'] *= 3.6      # convert from m/s to km/h
            else:
                # Skip interation, ABRP does not accept payload without location fields
                self.log.debug("location missing, skip... %s",payload)
                continue

            self.log.debug("Transmit...")

            try:
                payload_str = json.dumps(payload)
                ret = self.session.post(ApiUrl + "/send", data={'api_key': self.api_key, 'token': self.token, 'tlm': payload_str})
                self.log.debug("Post result: %i %s", ret.status_code, ret.json())

                if ret.status_code != requests.codes.ok or ret.json()['status'] != "ok":
                    self.log.error("Submit error: %s %s %s",payload_str,str(ret),ret.text)

                # XXX Need to reimplement, not working well
                #abrpSocThreshold = ABRP.getNextCharge()

            except requests.exceptions.ConnectionError as e:
                self.log.error(e)
            except SubmitError as e:
                self.log.error(e)

            # Prime next loop iteration
            if self.running:
                runtime = time() - now
                interval = self.poll_interval - (runtime if runtime > self.poll_interval else 0)
                if interval > 0:
                    sleep(interval)


    def getNextCharge(self):
        ret = self.session.get("{1}/get_next_charge?api_key={0.api_key}&token={0.token}".format(self, ApiUrl))
        if ret.status_code == requests.codes.ok and ret.json()['status'] == "ok":
            return ret.json()['next_charge']
        else:
            raise SubmitError(str(ret),ret.text)

    def checkWatchdog(self):
        return self.thread.is_alive()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    import json,sys
    with open('config.json', encoding='utf-8') as config_file:
        config = json.loads(config_file.read())

    sys.path.insert(0, 'cars')
    sys.path.insert(0, 'dongles')
    from IONIQ_BEV import IONIQ_BEV
    from FakeDongle import FakeDongle
    dongle = FakeDongle(config['dongle'])
    car = IONIQ_BEV(dongle)

    abrp = ABRP(config['abrp'], car, None, None)

    ret = abrp.getNextCharge()
    print(ret)

    ret = abrp.submit(car.readDongle(),{'latitude':56.0,'longitude':9.0,'speed':11.1,'altitude':9.9})
    print(ret,ret.text)

