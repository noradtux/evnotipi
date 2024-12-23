""" Module for the Renault Zoe Z.E.50 """
from .car import Car
from .isotp_decoder import IsoTpDecoder

LBC_RX = 0x18daf1db
LBC_TX = 0x18dadbf1
EVC_RX = 0x18daf1da
EVC_TX = 0x18dadaf1
BCB_RX = 0x18daf1de
BCB_TX = 0x18dadef1

CMD_AUX_VOLTAGE = bytes.fromhex('222005')  # EVC
CMD_CHARGE_STATE = bytes.fromhex('225017')  # BCB 0:Nok;1:AC mono;2:AC tri;3:DC;4:AC bi
CMD_SOC = bytes.fromhex('229002')  # EVC
CMD_SOC_BMS = bytes.fromhex('229001')  # LBC
CMD_VOLTAGE = bytes.fromhex('229006')
CMD_BMS_ENERGY = bytes.fromhex('229245')  # PR155 geladene Energie
CMD_ODO = bytes.fromhex('222006')  # EVC
CMD_NRG_DISCHARG = bytes.fromhex('229245')  # PR047
#CMD_CURRENT = bytes.fromhex('2221DA')  # EVC gemessener Strom
CMD_CURRENT = bytes.fromhex('229257')  # EVC berechneter Strom
CMD_SOH = bytes.fromhex('223206')  # EVC

Fields = [
        {'cmd': CMD_AUX_VOLTAGE, 'canrx': EVC_RX, 'cantx': EVC_TX, 'simple': True,
            'fields': ({'name': 'auxBatteryVoltage', 'scale': .01})},
        {'cmd': CMD_CHARGE_STATE, 'canrx': BCB_RX, 'cantx': BCB_TX, 'simple': True,
            'fields': ({'name': 'charge_state'})},
        {'cmd': CMD_SOC, 'canrx': LBC_RX, 'cantx': LBC_TX, 'simple': True,
            'fields': ({'name': 'SOC_DISPLAY', 'scale': .01})},
        {'cmd': CMD_SOC_BMS, 'canrx': LBC_RX, 'cantx': LBC_TX, 'simple': True,
            'fields': ({'name': 'SOC_BMS', 'scale': .01})},
        {'cmd': CMD_VOLTAGE, 'canrx': LBC_RX, 'cantx': LBC_TX, 'simple': True,
            'fields': ({'name': 'dcBatteryVoltage', 'scale': .001})},
        {'cmd': CMD_BMS_ENERGY, 'canrx': LBC_RX, 'cantx': LBC_TX, 'simple': True,
            'fields': ({'name': 'cumulativeEnergyCharged', 'scale': .001})},
        {'cmd': CMD_ODO, 'canrx': EVC_RX, 'cantx': EVC_TX,
            'fields': (
                {'padding': 3},
                {'name': 'odo', 'width': 3},
                )
            },
        {'cmd': CMD_NRG_DISCHARG, 'canrx': LBC_RX, 'cantx': LBC_TX, 'simple': True,
            'fields': ({'name': 'cumulativeEnergyDischarged', 'scale': .001})},
        {'cmd': CMD_CURRENT, 'canrx': LBC_RX, 'cantx': LBC_TX, 'simple': True,
            'fields': ({'name': 'dcBatteryCurrent', 'offset': (2**15) * .01, 'scale': -0.01})},
        # {'cmd': CMD_SOH, 'canrx': EVC_RX, 'cantx': EVC_TX,
        #    'fields': (
        #        {'padding': 3},
        #        {'name': 'soh', 'format': 'b'},
        #        )
        #    },
        {'computed': True,
            'fields': (
                {'name': 'dcBatteryPower',
                    'lambda': lambda d: d['dcBatteryCurrent'] * d['dcBatteryVoltage'] / 1000.0},
                {'name': 'charging',
                    'lambda': lambda d: int(d['charge_state'] != 0)},
                {'name': 'normalChargePort',
                    'lambda': lambda d: int(d['charge_state'] in (1, 2, 4))},
                {'name': 'rapidChargePort',
                    'lambda': lambda d: int(d['charge_state'] == 3)},
                )
            },
    ]


class ZoeZe50(Car):
    """ Class for Zoe ZE50 """

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
        return 'ZOE_ZE50'
