""" msgpack telemetry """
from time import monotonic
from lzma import compress, decompress
import logging
from msgpack import packb, unpackb
from requests import Session
from requests.exceptions import RequestException

log = logging.getLogger("EVNotiPi/TelemetryProxy")


def msg_encode(msg):
    """ encode and compress message """
    return compress(packb(msg))


def msg_decode(msg):
    """ decompress and decode message """
    return unpackb(decompress(msg), use_list=False)


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
        self._fields = None
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
        self._submit_settings()
        log.debug('Thread running')

    def stop(self):
        """ Stop the submission thread """
        assert self._running
        self._car.unregister_data(self.data_callback)
        self._running = False

    def _submit_settings(self):
        log.info('Submitting service settings')
        payload = msg_encode(self._backends)
        response = self._session.post(f'{self._base_url}/setsvcsettings/{self._car.id}',
                                      headers={'Authorization': self._auth},
                                      data=payload)
        assert response.status_code == 200
        data = msg_decode(response.content)
        self._fields = data['fields']
        log.debug('got fields (%s)', self._fields)

    def data_callback(self, data):
        """ Callback to receive data from "car" """
        now = monotonic()
        states = self._field_states
        points = self._points

        log.debug("Enqeue...")
        point = {
            'carid': self._car.id,
            'cartype': self._cartype,
            'akey': self._evn_akey,
            }

        for key, value in data.items():
            if value is None or \
                    (self._fields is not None and key not in self._fields):
                continue

            if key not in states:
                states[key] = {'next_interval': 0, 'last_value': None}

            if value != states[key]['last_value'] or \
                    now >= states[key]['next_interval']:

                states[key]['last_value'] = value
                states[key]['next_interval'] = now + 60

                point[key] = value

        points.append(point)

        if now >= self._next_transmit:
            self._next_transmit = now + self._interval
            payload = msg_encode(points)

            try:
                ret = self._session.post(self._transmit_url,
                                         headers={'Authorization': self._auth},
                                         data=payload)
                if ret.status_code == 402:  # Server requests settings
                    states.clear()          # also make sure we send all values on next try
                    points.clear()
                    self._submit_settings()
                else:
                    points.clear()
            except RequestException as exception:
                log.warning(str(exception))
                self._session.close()

    def check_thread(self):
        """ Return the status of the thread """
        return self._running
