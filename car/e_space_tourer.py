""" Module for Citroën ë-SpaceTourer """
from time import time
from threading import Thread, Lock
import logging
from .car import Car, ifbu, ifbs
from dongle import NoData

class ESpaceTourer(Car):
    """ Class for E208 """

    def __init__(self, config, dongle, watchdog, gps):
        if config.get('interval', 0) < 1:
            config['interval'] = 1

        Car.__init__(self, config, dongle, watchdog, gps)
        self._dongle.set_protocol('CAN_11_500')
        self._dongle.set_raw_filters_ex([
            {'id': 0x3f4, 'mask': 0x7ff},
        #    {'id': 0x1f6, 'mask': 0x7ff},
        #    {'id': 0x29a, 'mask': 0x7ff},
        #    {'id': 0x35c, 'mask': 0x7ff},
        #    {'id': 0x427, 'mask': 0x7ff},
        #    {'id': 0x42e, 'mask': 0x7ff},
        #    {'id': 0x5d7, 'mask': 0x7ff},
        #    {'id': 0x637, 'mask': 0x7ff},
        #    {'id': 0x638, 'mask': 0x7ff},
        #    {'id': 0x652, 'mask': 0x7ff},
        #    {'id': 0x654, 'mask': 0x7ff},
        #    {'id': 0x656, 'mask': 0x7ff},
        #    {'id': 0x658, 'mask': 0x7ff},
        #    {'id': 0x6f8, 'mask': 0x7ff},
        #    {'id': 0x7bb, 'mask': 0x7ff},
            ])
        self._data = self.get_base_data()
        self._data = {}
        self._data_lock = Lock()
        self._reader_thread = Thread(name="CAN-Reader-Thread", target=self.reader_thread)
        self._reader_running = False
        self._running = False
        self._last_data = time()

    def start(self):
        Car.start(self)
        self._reader_running = True
        self._reader_thread.start()

    def stop(self):
        if self._running:
            self._reader_running = False
            self._reader_thread.join()
        Car.stop(self)

    def reader_thread(self):
        while self._reader_running:
            try:
                data = self._dongle.read_raw_frame(1)
                self._last_data = time()

                with self._data_lock:
                    can_id = data['can_id']
                    msg = data['data']

                    if self._log.isEnabledFor(logging.DEBUG):
                        self._log.debug("data can_id(%x) msg(%s)", can_id, msg.hex())


            except NoData:
                self._log.debug('NoData')

    def read_dongle(self, data):
        if time() - self._last_data > 5:
            raise NoData

        with self._data_lock:
            data.update(self._data)

    def get_base_data(self):
        return {
                "CAPACITY": 75,
                "SLOW_SPEED": 3.6,
                "NORMAL_SPEED": 11.0,
                "FAST_SPEED": 100.0
                }

    def get_abrp_model(self):
        return 'peugeot:etraveler:21:%d:citroen' % self.get_base_data()['CAPACITY']

    def get_evn_model(self):
        return 'ESPACETOURER'
