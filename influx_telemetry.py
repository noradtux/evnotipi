#!/usr/bin/env python3

from datetime import datetime, timezone
from time import time, sleep
from threading import Thread, Condition
import logging
import influxdb
import pyrfc3339

INT_FIELD_LIST = ('gps_device', 'charging', 'fanFeedback', 'fanStatus', 'fix_mode',
                  'normalChargePort', 'rapidChargePort', 'submit_queue_len',
                  'timestamp')

class InfluxTelemetry:
    def __init__(self, config, car, gps, evnotify):
        self._log = logging.getLogger("EVNotiPi/InfluxDB")
        self._log.info("Initializing InfluxDB")

        self._evn_akey = evnotify.config['akey']
        self._car = car
        self._cartype = car.getEVNModel()
        self._gps = gps
        self._poll_interval = config['interval']
        self._running = False
        self._thread = None

        try:
            influx = influxdb.InfluxDBClient(config['host'], config['port'],
                                             config['user'], config['pass'],
                                             config['dbname'], retries=1, timeout=5,
                                             ssl=config['ssl'] if 'ssl' in config else False,
                                             verify_ssl=True, compression=9)

        except influxdb.exceptions.InfluxDBClientError as e:
            self._log.error(e)
            influx = None
        except influxdb.exceptions.InfluxDBServerError as e:
            self._log.error(e)
            influx = None

        self._influx = influx
        self.data_q_lock = Condition()
        self.data_queue = []

    def start(self):
        if self._influx:
            self._running = True
            self._thread = Thread(target=self.submitData, name="EVNotiPi/InfluxDB")
            self._thread.start()
            self._car.registerData(self.dataCallback)

    def stop(self):
        self._car.unregisterData(self.dataCallback)
        self._running = False
        with self.data_q_lock:
            self.data_q_lock.notify()
        self._thread.join()

    def dataCallback(self, data):
        self._log.debug("Enqeue...")
        with self.data_q_lock:
            tags = {
                "cartype": self._cartype,
                "akey": self._evn_akey,
                }
            fields = {k:v if k in INT_FIELD_LIST else float(v)
                      for k, v in data.items() if v is not None}
            fields['submit_queue_len'] = len(self.data_queue)

            if 'gps_device' in data:
                tags['gps_device'] = data['gps_device']

            self.data_queue.append({
                "measurement": "telemetry",
                "time": pyrfc3339.generate(datetime.fromtimestamp(data['timestamp'], timezone.utc)),
                "tags": tags,
                "fields": fields
                })

            self.data_q_lock.notify()

    def submitData(self):
        while self._running:
            now = time()
            did_transfer = False
            with self.data_q_lock:
                if len(self.data_queue) == 0:
                    self._log.debug("Waiting...")
                    self.data_q_lock.wait()
                else:
                    self._log.debug("Transmit...")

                    try:
                        self._influx.write_points(self.data_queue)
                        self.data_queue.clear()
                        did_transfer = True         # sleep outside of the lock
                    except influxdb.exceptions.InfluxDBClientError as e:
                        self._log.error("InfluxDBClientError qlen(%i): code(%i) content(%s)",
                                        len(self.data_queue), e.code, e.content)
                        if e.code == 400:
                            self.data_queue.clear()
                    except Exception as e:
                        self._log.error("InfluxTelemetry len(%i): %s", len(self.data_queue), e)

            # Prime next loop iteration
            if self._running and did_transfer:
                runtime = time() - now
                interval = self._poll_interval - (runtime if runtime > self._poll_interval else 0)
                sleep(max(0, interval))


    def checkWatchdog(self):
        return self._thread.is_alive()
