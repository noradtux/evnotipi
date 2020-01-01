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

class ABRP:
    def __init__(self, config, car, gps, evnotify):
        self.log = logging.getLogger("EVNotiPi/ABRP")
        self.log.info("Initializing ABRP")

        self.car = car
        self.car_model = car.getABRPModel()
        self.gps = gps
        self.config = config
        self.session = requests.Session()
        self.api_key = config['api_key']
        self.token = config['token']
        self.poll_interval = config['interval']
        self.running = False
        self.thread = None
        self.watchdog = time()
        self.watchdog_timeout = self.poll_interval * 10
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
            self.data.append(data)
            self.data_lock.notify()

    def submitData(self):
        while self.running:
            with self.data_lock:
                self.data_lock.wait()
                data = self.data[-1:]
                pwr_cnt = 0
                gps_cnt = 0
                for d in self.data[:-1]:
                    if d['dcBatteryCurrent'] and d['dcBatteryPower'] and d['dcBatteryVoltage']:
                        data['dcBatteryCurrent'] += d['dcBatteryCurrent']
                        data['dcBatteryPower']   += d['dcBatteryPower']
                        data['dcBatteryVoltage'] += d['dcBatteryVoltage']
                        pwr_cnt += 1
                    if d['speed'] and d['latitude'] and d['longitude']:
                        data['speed']       += d['speed']
                        data['latitude']    += d['latitude']
                        data['longitude']   += d['longitude']
                        gps_cnt += 1

                data['dcBatteryCurrent'] /= pwr_cnt
                data['dcBatteryPower']   /= pwr_cnt
                data['dcBatteryVoltage'] /= pwr_cnt

                data['speed']       /= gps_cnt
                data['speed']       *= 3.6      # convert from m/s to km/h
                data['latitude']    /= gps_cnt
                data['longitude']   /= gps_cnt

                self.data.clear()

            now = time()
            self.watchdog = now

            try:
                payload = {
                        'utc':       data['timestamp'],
                        'car_model': self.car_model,
                        }

                payload.update({v:data[k] for k,v in PidMap.items() if data[k] != None})

                payload_str = json.dumps(payload)
                self.log.debug(ApiUrl + "/send", {'api_key': self.api_key, 'token': self.token, 'tlm': payload_str})

                ret = self.session.post(ApiUrl + "/send", data={'api_key': self.api_key, 'token': self.token, 'tlm': payload_str})
                if ret.status_code == requests.codes.ok and ret.json()['status'] == "ok":
                    return ret
                else:
                    self.log.error("Submit error: %s %s %s",payload_str,str(ret),ret.text)

                # XXX Need to reimplement, not working well
                #abrpSocThreshold = ABRP.getNextCharge()

            except requests.exceptions.ConnectionError:
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
        return self.thread.is_alive() # (time() - self.watchdog) <= self.watchdog_timeout


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

