""" Influx Telemetry """
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
    """ Submit all available data to anm influxdb """

    def __init__(self, config, car, gps, evnotify):
        self._log = logging.getLogger("EVNotiPi/InfluxDB")
        self._log.info("Initializing InfluxDB")

        self._config = config
        self._evn_akey = evnotify.config['akey']
        self._car = car
        self._cartype = car.getEVNModel()
        self._gps = gps
        self._poll_interval = config['interval']
        self._running = False
        self._thread = None

        self._data_q_lock = Condition()
        self._data_queue = []

    def start(self):
        """ Start the submission thread """
        self._running = True
        self._thread = Thread(target=self.submit_data, name="EVNotiPi/InfluxDB")
        self._thread.start()
        self._car.registerData(self.data_callback)

    def stop(self):
        """ Stop the submission thread """
        self._car.unregisterData(self.data_callback)
        self._running = False
        with self._data_q_lock:
            self._data_q_lock.notify()
        self._thread.join()

    def data_callback(self, data):
        """ Callback to receive data from "car" """
        self._log.debug("Enqeue...")
        with self._data_q_lock:
            tags = {
                "cartype": self._cartype,
                "akey": self._evn_akey,
                }
            fields = {k: v if k in INT_FIELD_LIST else float(v)
                      for k, v in data.items() if v is not None}

            if 'gps_device' in data:
                tags['gps_device'] = data['gps_device']

            self._data_queue.append({
                "measurement": "telemetry",
                "time": pyrfc3339.generate(datetime.fromtimestamp(data['timestamp'], timezone.utc)),
                "tags": tags,
                "fields": fields
                })

            self._data_q_lock.notify()

    def submit_data(self):
        """ The submission thread """
        influx = None
        while self._running and influx is None:
            try:
                influx = influxdb.InfluxDBClient(self._config['host'], self._config['port'],
                                                 self._config['user'], self._config['pass'],
                                                 self._config['dbname'], retries=1, timeout=30,
                                                 ssl=self._config.get('ssl', False),
                                                 verify_ssl=True, gzip=True)

            except influxdb.exceptions.InfluxDBClientError as err:
                self._log.error(err)
                influx = None
                sleep(3)
            except influxdb.exceptions.InfluxDBServerError as err:
                self._log.error(err)
                influx = None
                sleep(3)

        send_queue = []
        while self._running:
            now = time()
            did_transfer = False
            with self._data_q_lock:
                if len(self._data_queue) == 0:
                    self._log.debug("Waiting...")
                    self._data_q_lock.wait()
                else:
                    self._log.debug("Transmit...")

                    send_queue += self._data_queue
                    self._data_queue.clear()

            try:
                influx.write_points(send_queue)
                send_queue.clear()
                did_transfer = True         # sleep outside of the lock
            except influxdb.exceptions.InfluxDBClientError as err:
                self._log.error("InfluxDBClientError qlen(%i): code(%i) content(%s)",
                                len(send_queue), err.code, err.content)
                if err.code == 400:
                    send_queue.clear()
            except Exception as err:
                self._log.error("InfluxTelemetry len(%i): %s", len(send_queue), err)

            # Prime next loop iteration
            if self._running and did_transfer:
                runtime = time() - now
                interval = self._poll_interval - (runtime if runtime > self._poll_interval else 0)
                sleep(max(0, interval))


    def check_thread(self):
        """ Return the status of the thread """
        return self._thread.is_alive()
