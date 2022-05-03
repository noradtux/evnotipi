""" Module for the Smart ED """

from time import monotonic
from threading import Thread, Lock
import logging
from .car import Car, ifbu, ifbs
from .isotp_decoder import IsoTpDecoder
from dongle import NoData

BattHWrev = bytes.fromhex('22f150')
BattSWrev = bytes.fromhex('22f151')
BattVIN = bytes.fromhex('22f190')
BattTemps = bytes.fromhex('220201')
BattModuleTemps = bytes.fromhex('220202')
BattHVStatus = bytes.fromhex('220204')
BattADCref = bytes.fromhex('220207')
BattVolts = bytes.fromhex('220208')
BattIsolation = bytes.fromhex('220209')
BattAmps = bytes.fromhex('220203')
BattDate = bytes.fromhex('220304')
BattProdDate = bytes.fromhex('22F18C')
BattCapacity = bytes.fromhex('220310')
BattHVContactorCyclesLeft = bytes.fromhex('22030B')
BattHVContactorMax = bytes.fromhex('22030C')
BattHVContactorState = bytes.fromhex('22D000')
CarVIN = bytes.fromhex('090200')
# Experimental readouts
BattCapInit = bytes.fromhex('220305')
BattCapLoss = bytes.fromhex('220309')
BattUnknownCounter = bytes.fromhex('220101')

CoolingTemp = bytes.fromhex('222047')
CoolingPumpTemp = bytes.fromhex('22230A')
CoolingPumpLV = bytes.fromhex('222308')
CoolingPumpAmps = bytes.fromhex('222309')
CoolingPumpRPM = bytes.fromhex('22D032')
CoolingPumpOTR = bytes.fromhex('226309')  # operating time record
CoolingFanRPM = bytes.fromhex('22D041')
CoolingFanOTR = bytes.fromhex('22630A')
BatteryHeaterOTR = bytes.fromhex('226321')
BatteryHeaterON = bytes.fromhex('22D302')
VacuumPumpOTR = bytes.fromhex('226303')
VacuumPumpPress1 = bytes.fromhex('222041')
VacuumPumpPress2 = bytes.fromhex('222043')

ChargerPN_HW = bytes.fromhex('22F111')
ChargerSWrev = bytes.fromhex('22F121')
ChargerVoltages = bytes.fromhex('220226')
ChargerAmps = bytes.fromhex('220225')
ChargerSelCurrent = bytes.fromhex('22022A')
ChargerTemperatures = bytes.fromhex('220223')

RawFilters = (
        {'id': 0x518, 'mask': 0x7ff},   # SOC_DISPLAY
        {'id': 0x2d5, 'mask': 0x7ff},   # SOC_BMS
        {'id': 0x508, 'mask': 0x7ff},   # Current
        {'id': 0x448, 'mask': 0x7ff},   # Voltage
        {'id': 0x3d5, 'mask': 0x7ff},   # Aux Voltage
        {'id': 0x412, 'mask': 0x7ff},   # ODO
        )

Fields = (
        {'cmd': BattHVStatus, 'cantx': 0x7e7, 'canrx': 0x7ef, 'autopad': True,
            'fields': (
                {'padding': 12},
                {'name': 'dcBatteryVoltage', 'width': 2, 'scale': 1/64}
                )
            },
        {'cmd': BattAmps, 'cantx': 0x7e7, 'canrx': 0x7ef, 'autopad': True,
            'fields': (
                {'padding': 3},
                {'name': 'dcBatteryCurrent', 'width': 2, 'signed': True, 'scale': 1/32}
                )
            },
        {'computed': True,
            'fields': (
                {'name': 'dcBatteryPower',
                    'lambda': lambda d: d['dcBatteryCurrent'] * d['dcBatteryVoltage'] / 1000.0},
                {'name': 'charging',
                    'lambda': lambda d: int(d['bmsBits1'] & 0x80 != 0)},
                {'name': 'normalChargePort',
                    'lambda': lambda d: int(d['bmsBits1'] & 0x20 != 0)},
                {'name': 'rapidChargePort',
                    'lambda': lambda d: int(d['bmsBits1'] & 0x40 != 0)},
                )
            },
        )


class SmartED(Car):
    """ Class for Smart ED """

    def __init__(self, config, dongle, watchdog, gps):
        if config.get('interval', 0) < 1:
            config['interval'] = 1
        Car.__init__(self, config, dongle, watchdog, gps)
        self._dongle.set_protocol('CAN_11_500')
        #self._isotp = IsoTpDecoder(self._dongle, Fields)
        self._reader_thread = Thread(name="SmartED-Reader-Thread", target=self._reader_thread)
        self._reader_running = False
        self._data = {}
        self._data_lock = Lock()
        self._last_data = 0

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
        filter_idx = 0
        filters_len = len(RawFilters)
        dongle = self._dongle
        data = self._data
        data.update(self.get_base_data())

        dongle.set_raw_filters_ex((RawFilters[filter_idx]))

        while self._reader_running:
            try:
                data = dongle.read_raw_frame(1)
                self._last_data = monotonic()

                with self._data_lock:
                    can_id = data['can_id']
                    msg = data['data']

                    if self._log.isEnabledFor(logging.DEBUG):
                        self._log.debug("data can_id(%x) msg(%s)", can_id, msg.hex())

                    success = True

                    if can_id == 0x518:
                        data['SOC_DISPLAY'] = msg[7] / 2
                    elif can_id == 0x2d5:
                        data['SOC_BMS'] = ((msg[4] & 0x03) << 8) + msg[5]
                    elif can_id == 0x508:
                        data['dcBatteryCurrent'] = (((msg[2] & 0x3f) << 8) + msg[5] - 0x2000) * .1
                    elif can_id == 0x448:
                        data['dcBatteryVoltage'] = ((msg[6] << 8) + msg[7]) * .1
                    elif can_id == 0x3d5:
                        data['auxBatteryVoltage'] = msg[3] * .1
                    elif can_id == 0x412:
                        data['odo'] = (msg[2] << 16) + (msg[3] << 8) + msg[4]
                    else:
                        success = False

                    if success:
                        if (can_id in (0x508, 0x448) and
                                'dcBatteryCurrent' in self._data and
                                'dcBatteryVoltage' in self._data):
                            data['dcBatteryPower'] = \
                                data['dcBatteryCurrent'] * data['dcBatteryVoltage'] / 1000

                        filter_idx = (filter_idx + 1) % filters_len
                        dongle.set_raw_filters_ex((RawFilters[filter_idx]))

            except NoData:
                self._log.debug('NoData')

    def read_dongle(self, data):
        """ Fetch data from CAN-bus and decode it.
            "data" needs to be a dictionary that will
            be modified with decoded data """
        with self._data_lock:
            data.update(self._data)

    def get_base_data(self):
        return {
            "CAPACITY": 17,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 22.0
        }

    def get_abrp_model(self):
        return 'smart:ed4:17:18:fortwo'

    def get_evn_model(self):
        return 'SMART_ED'
