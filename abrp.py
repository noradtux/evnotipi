#!/usr/bin/env python3

import requests
from time import time, sleep
import json
import logging
from threading import Thread, Lock

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

    def start(self):
        self.running = True
        self.thread = Thread(target = self.submitData)
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()

    def submitData(self):
        while self.running:
            now = time()
            self.watchdog = now

            data = self.car.getData()
            if data:
                fix = self.gps.fix()
                if fix and fix.mode > 1:
                    location = {
                            'latitude':  fix.latitude,
                            'longitude': fix.longitude,
                            }
                    if fix.mode > 2:
                        location.update({
                            'altitude':fix.altitude,
                            'speed': fix.speed,
                            })
                else:
                    location = None

                try:
                    self.submit(data, location)

                    # XXX Need to reimplement, not working well
                    #abrpSocThreshold = ABRP.getNextCharge()

                    #if is_charging and \
                    #        last_charging_soc < abrpSocThreshold and \
                    #        currentSOC >= abrpSocThreshold:
                    #    EVNotify.sendNotification()

                #except EVNotify.CommunicationError as e:
                #    self.log.error(e)
                except SubmitError as e:
                    self.log.error(e)

            # Prime next loop iteration
            if self.running:
                runtime = time() - now
                interval = self.poll_interval - (runtime if runtime > self.poll_interval else 0)
                sleep(interval)


    def submit(self, data, location):
        payload = {
                'utc':       data['timestamp'],
                'car_model': self.car_model,
                }

        for k,v in PidMap.items():
            if k in data:
                payload[v] = data[k]
            elif 'EXTENDED' in data and k in data['EXTENDED']:
                payload[v] = data['EXTENDED'][k]
            elif 'ADDITIONAL' in data and k in data['ADDITIONAL']:
                payload[v] = data['ADDITIONAL'][k]
            elif location and k in location:
                payload[v] = location[k] * (3.6 if k == 'speed' else 1)

        payload_str = json.dumps(payload)
        self.log.debug(ApiUrl + "/send", {'api_key': self.api_key, 'token': self.token, 'tlm': payload_str})
        try:
            ret = self.session.post(ApiUrl + "/send", data={'api_key': self.api_key, 'token': self.token, 'tlm': payload_str})
            if ret.status_code == requests.codes.ok and ret.json()['status'] == "ok":
                return ret
            else:
                raise SubmitError("Submit error:",payload_str,str(ret),ret.text)
        except requests.exceptions.ConnectionError:
            raise SubmitError()


    def getNextCharge(self):
        ret = self.session.get("{1}/get_next_charge?api_key={0.api_key}&token={0.token}".format(self, ApiUrl))
        if ret.status_code == requests.codes.ok and ret.json()['status'] == "ok":
            return ret.json()['next_charge']
        else:
            raise SubmitError(str(ret),ret.text)

    def checkWatchdog(self):
        return (time() - self.watchdog) <= self.watchdog_timeout


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

