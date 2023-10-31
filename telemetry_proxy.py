""" msgpack telemetry """
from time import monotonic
import lzma
import logging
import msgpack
from requests import Session
from requests.exceptions import RequestException

INT_FIELD_LIST = ('charging', 'fanFeedback', 'fanStatus', 'fix_mode',
                  'normalChargePort', 'rapidChargePort', 'submit_queue_len')
STR_FIELD_LIST = ('cartype', 'akey', 'gps_device')

log = logging.getLogger("EVNotiPi/TelemetryProxy")


class TelemetryProxy:
    """ Submit all available data to anm influxdb """

    def __init__(self, config, car, gps, evnotify):
        log.info("Initializing MsgPack")

        self._backends = config['backends']
        self._evn_akey = evnotify._config['akey']
        self._car = car
        self._cartype = car.get_evn_model()
        self._gps = gps
        self._interval = config.get('interval', 5)
        self._field_states = {}
        self._next_transmit = 0
        self._points = []
        self._base_url = config['url']
        self._auth = config['authorization']
        self._transmit_url = f'{self._base_url}/transmit/{self._car.id}'
        self._session = Session()
        self._websocket = None
        self._running = False

    def start(self):
        """ Start the submission thread """
        log.debug('Starting thread')
        assert not self._running
        self._running = True
        self._car.register_data(self.data_callback)
        log.debug('Thread running')

    def stop(self):
        """ Stop the submission thread """
        assert self._running
        self._car.unregister_data(self.data_callback)
        self._running = False

    def _submit_settings(self):
        msg = msgpack.packb(self._backends)
        payload = lzma.compress(msg)
        self._session.post(f'{self._base_url}/setsvcsettings/{self._car.id}',
                           headers={'Authorization': self._auth},
                           data=payload)

    def data_callback(self, data):
        """ Callback to receive data from "car" """
        now = monotonic()
        states = self._field_states
        points = self._points

        log.debug("Enqeue...")
        point = {"tags": {
            "cartype": self._cartype,
            "carid": self._car.id,
            "akey": self._evn_akey,
            }
                 }

        fields = {}
        for key, value in data.items():
            if value is None:
                continue

            if key in STR_FIELD_LIST:
                point['tags'][key] = value
            else:
                if key not in states:
                    states[key] = {'next_interval': 0, 'last_value': None}

                if value != states[key]['last_value'] or \
                        now >= states[key]['next_interval']:

                    states[key]['last_value'] = value
                    states[key]['next_interval'] = now + 60

                    fields[key] = int(value) if key in INT_FIELD_LIST \
                        else float(value)

        point['time'] = data['timestamp']
        point['fields'] = fields

        points += [point]

        if now >= self._next_transmit:
            self._next_transmit = now + self._interval
            msg = msgpack.packb(points)
            points.clear()
            payload = lzma.compress(msg)

            try:
                while True:
                    ret = self._session.post(self._transmit_url,
                                             headers={'Authorization': self._auth},
                                             data=payload)
                    if ret.status_code == 402:  # Server requests settings
                        self._submit_settings()
                    else:
                        break
            except RequestException as exception:
                log.warning(str(exception))
                self._session.close()

    def check_thread(self):
        """ Return the status of the thread """
        return self._running
