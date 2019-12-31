#!/usr/bin/env python3

import threading
import influxdb
import pyrfc3339
from datetime import datetime, timezone
from time import time, sleep
from threading import Thread, Condition
import logging
from math import isnan

class InfluxTelemetry:
    def __init__(self, config, car, gps, evnotify):
        self.log = logging.getLogger("EVNotiPi/InfluxDB")
        self.log.info("Initializing InfluxDB")

        self.evn_akey = evnotify.config['akey']
        self.car = car
        self.cartype = car.getEVNModel()
        self.gps = gps
        self.poll_interval = config['interval']
        self.running = False
        self.thread = None
        self.watchdog = time()
        self.watchdog_timeout = self.poll_interval * 10

        try:
            Influx = influxdb.InfluxDBClient(config['host'], config['port'],
                    config['user'], config['pass'], config['dbname'],
                    retries=1, timeout=1, ssl=config['ssl'] if 'ssl' in config else False, verify_ssl=True)

        except influxdb.exceptions.InfluxDBClientError as e:
            self.log.error(e)
            Influx = None
        except influxdb.exceptions.InfluxDBServerError as e:
            self.log.error(e)
            Influx = None

        self.influx = Influx
        self.data_q_lock = Condition()
        self.data_queue = []

    def start(self):
        if self.influx:
            self.running = True
            self.thread = Thread(target = self.submitData, name = "EVNotiPi/InfluxDB")
            self.thread.start()
            self.car.registerData(self.dataCallback)

    def stop(self):
        self.car.unregisterData(self.dataCallback)
        self.running = False
        with self.data_q_lock:
            self.data_q_lock.notify()
        self.thread.join()

    def dataCallback(self, data):
        self.log.debug("Enqeue...")
        with self.data_q_lock:
            if data and 'timestamp' in data:
                fix = self.gps.fix()
                tags = {
                        "cartype": self.cartype,
                        "akey": self.evn_akey,
                        }

                fields = {}
                if 'SOC_DISPLAY' in data:
                    fields.update({
                        'SOC_DISPLAY': data['SOC_DISPLAY'],
                        })
                if 'SOC_BMS' in data:
                    fields.update({
                        'SOC_BMS': data['SOC_BMS'],
                        })

                if 'EXTENDED' in data:
                    fields.update(data['EXTENDED'])
                if 'ADDITIONAL' in data:
                    fields.update(data['ADDITIONAL'])

                if fix and fix.mode > 1:
                    fields.update({
                            'latitude':  float(fix.latitude),
                            'longitude': float(fix.longitude),
                            'gdop':      float(fix.gdop),
                            'pdop':      float(fix.pdop),
                            'hdop':      float(fix.hdop),
                            'vdop':      float(fix.vdop),
                            'distance':  float(fix.distance),
                            })
                    if not isnan(fix.speed):
                        fields.update({
                            'speed':     float(fix.speed),
                            })
                    if fix.mode > 2 and not isnan(fix.altitude):
                        fields.update({
                            'altitude':  float(fix.altitude),
                            })
                    if fix.device:
                        tags.update({
                            'gps_device': fix.device
                            })

                self.data_queue.append({
                    "measurement": "telemetry",
                    "time": pyrfc3339.generate(datetime.fromtimestamp(data['timestamp'], timezone.utc)),
                    "tags": tags,
                    "fields": {**fields, 'submit_queue_len': len(self.data_queue)}
                    })

                self.data_q_lock.notify()

    def submitData(self):
        while self.running:
            now = time()
            did_transfer = False
            with self.data_q_lock:
                if len(self.data_queue) == 0:
                    self.log.debug("Waiting...")
                    self.data_q_lock.wait()
                else:
                    self.log.debug("Got Data...")

                    try:
                        self.influx.write_points(self.data_queue)
                        self.data_queue.clear()
                        did_transfer = True         # sleep outside of the lock
                    except influxdb.exceptions.InfluxDBClientError as e:
                        self.log.error("InfluxDBClientError qlen({}): code({}) content({}) last_data({})".format(len(self.data_queue), str(e.code), str(e.content), self.data_queue[-1]))
                        if e.code == 400:
                            self.data_queue.clear()
                    except Exception as e:
                        self.log.error("InfluxTelemetry len({}): {}".format(len(self.data_queue), str(e)))

            # Prime next loop iteration
            if self.running and did_transfer:
                runtime = time() - now
                interval = self.poll_interval - (runtime if runtime > self.poll_interval else 0)
                if interval > 0:
                    sleep(interval)


    def checkWatchdog(self):
        return self.thread.is_alive() # (time() - self.watchdog) <= self.watchdog_timeout
