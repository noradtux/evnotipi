""" Influx Telemetry """
from datetime import datetime, timezone
from time import time, monotonic, sleep
import logging
from influxdb_client import InfluxDBClient, WriteOptions
import pyrfc3339

INT_FIELD_LIST = ('charging', 'fanFeedback', 'fanStatus', 'fix_mode',
                  'normalChargePort', 'rapidChargePort', 'submit_queue_len',
                  'timestamp')
STR_FIELD_LIST = ('gps_device')

class InfluxTelemetry:
    """ Submit all available data to anm influxdb """

    def __init__(self, config, car, gps, evnotify):
        self._log = logging.getLogger("EVNotiPi/InfluxDB")
        self._log.info("Initializing InfluxDB")

        self._config = config
        self._evn_akey = evnotify._config['akey']
        self._car = car
        self._cartype = car.get_evn_model()
        self._gps = gps
        self._poll_interval = config.get('interval', 60)
        self._batch_size = config.get('batch_size', 1048576)
        self._influx = None
        self._iwrite = None
        self._field_states = {}

    def start(self):
        """ Start the submission thread """
        self._running = True
        self._influx = InfluxDBClient(url=self._config['url'],
                                      org=self._config['org'],
                                      token=self._config['token'],
                                      enable_gzip=True)
        opts = WriteOptions(batch_size=self._batch_size,
                            flush_interval=self._poll_interval * 1000,
                            jitter_interval=5000)
        self._iwrite = self._influx.write_api(write_options=opts)
        self._car.register_data(self.data_callback)

    def stop(self):
        """ Stop the submission thread """
        self._car.unregister_data(self.data_callback)
        self._running = False
        self._iwrite.__del__()
        self._influx.__del__()
        self._influx = None
        self._iwrite = None

    def data_callback(self, data):
        """ Callback to receive data from "car" """
        now = monotonic()
        states = self._field_states

        self._log.debug("Enqeue...")
        p = {"measurement": "telemetry",
             "tags": {
                 "cartype": self._cartype,
                 "akey": self._evn_akey,
                 }
             }

        fields = {}
        for key, value in data.items():
            if value is None or key in STR_FIELD_LIST:
                continue

            if key not in states:
                states[key] = {'next_interval': 0, 'last_value': None}

            if value != states[key]['last_value'] or \
                    now >= states[key]['next_interval']:

                states[key]['last_value'] = value
                states[key]['next_interval'] = now + 60

                fields[key] = int(value) if key in INT_FIELD_LIST else float(value)

        if 'gps_device' in data:
            p['tags']['gps_device'] = data['gps_device']

        p["time"] = pyrfc3339.generate(datetime.fromtimestamp(data['timestamp'], timezone.utc))
        p["fields"] = fields

        try:
            self._iwrite.write(bucket=self._config['bucket'],
                               org=self._config['org'],
                               record=[p])
        except Exception as e:
            self._log.warning(str(e))

    def check_thread(self):
        """ Return the status of the thread """
        return self._running
