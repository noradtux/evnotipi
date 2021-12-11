""" Module for the Stellantis PSA platform """
from .car import Car
from .isotp_decoder import IsoTpDecoder

BMS_RX = 0x6b4
BMS_TX = 0x694
XXX_RX = 0x6a2  # don't know what device that is. Provides ext_temp, though
XXX_TX = 0x682
#22D815 ---> Battery voltage
#22D816 ---> Battery current
#22D86F ---> Battery minimum voltage
#22D870 ---> Battery maximum voltage
#22D410 ---> SOC calibrated
#22D865 ---> kWh available
#22D860 ---> SOH
#22D810 ---> SOC

Fields = [
        {'cmd': '22d815', 'canrx': BMS_RX, 'cantx': BMS_TX, 'simple': True,
            'fields': ({'name': 'dcBatteryVoltage', 'scale': 1/16, 'offset': -1200})},
        {'cmd': '22d816', 'canrx': BMS_RX, 'cantx': BMS_TX, 'simple': True,
            'fields': ({'name': 'dcBatteryCurrent', 'scale': 1/512})},
        {'cmd': '22d86f', 'canrx': BMS_RX, 'cantx': BMS_TX, 'simple': True,
            'fields': ({'name': 'cellMinVoltage', 'scale': .001})},
        {'cmd': '22d870', 'canrx': BMS_RX, 'cantx': BMS_TX, 'simple': True,
            'fields': ({'name': 'cellMaxVoltage', 'scale': .001})},
        {'cmd': '22d8ef', 'canrx': BMS_RX, 'cantx': BMS_TX, 'simple': True,
            'fields': ({'name': 'batteryMaxTemperature', 'signed': True})},
        {'cmd': '22d410', 'canrx': BMS_RX, 'cantx': BMS_TX, 'simple': True,
            'fields': ({'name': 'SOC_DISPLAY', 'scale': 1/512})},
        {'cmd': '22d860', 'canrx': BMS_RX, 'cantx': BMS_TX, 'simple': True,
            'fields': ({'name': 'soh', 'scale': 1/16})},
        {'cmd': '22d434', 'canrx': XXX_RX, 'cantx': XXX_TX, 'simple': True,
            'fields': ({'name': 'externalTemperature', 'signed': True})},
        {'computed': True,
            'fields': (
                {'name': 'dcBatteryPower',
                    'lambda': lambda d: d['dcBatteryCurrent'] * d['dcBatteryVoltage'] / 1000.0},
                # {'name': 'charging',
                #    'lambda': lambda d: int(d['charge_state'] in (4, 6))},
                # {'name': 'normalChargePort',
                #    'lambda': lambda d: int(d['charge_state'] == 4)},
                # {'name': 'rapidChargePort',
                #    'lambda': lambda d: int(d['charge_state'] == 6)},
                )},
    ]


class Psa(Car):
    """ Class for PSA """

    def __init__(self, config, dongle, watchdog, gps):
        Car.__init__(self, config, dongle, watchdog, gps)
        self._dongle.set_protocol('CAN_29_500')

        self._isotp = IsoTpDecoder(self._dongle, Fields)

    def read_dongle(self, data):
        """ Read and parse data from dongle """
        data.update(self.get_base_data())
        data.update(self._isotp.get_data())

    @staticmethod
    def get_base_data():
        return {
            "CAPACITY": 52,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 22.0,
            "FAST_SPEED": 50.0
        }

    @staticmethod
    def get_abrp_model():
        return ''

    @staticmethod
    def get_evn_model():
        return 'PSA'
