""" Module for the Chevy Bolt """
from .car import Car
from .isotp_decoder import IsoTpDecoder

Fields = (
        {'cmd': bytes.fromhex('2243af'), 'canrx': 0x7ec, 'cantx': 0x7e4, 'autopad': True,
            'fields': (
                {'padding': 2},                                                     # _,_
                {'name': 'SOC_BMS', 'width': 2, 'scale': 100/65535},                # A
                )
         },
        {'cmd': bytes.fromhex('228334'), 'canrx': 0x7ec, 'cantx': 0x7e4, 'autopad': True,
            'fields': (
                {'padding': 2},                                                     # _,_
                {'name': 'SOC_DISPLAY', 'width': 1, 'scale': 100/255},              # A
                )
         },
        {'cmd': bytes.fromhex('224349'), 'canrx': 0x7ec, 'cantx': 0x7e4, 'autopad': True,
            'fields': (
                {'padding': 2},                                                     # _,_
                {'name': 'batteryMaxTemperature', 'width': 1, 'offset': -40},       # A
                )
         },
        {'cmd': bytes.fromhex('22434A'), 'canrx': 0x7ec, 'cantx': 0x7e4, 'autopad': True,
            'fields': (
                {'padding': 2},                                                     # _,_
                {'name': 'batteryMinTemperature', 'width': 1, 'offset': -40},       # A
                )
         },
        {'cmd': bytes.fromhex('2241A4'), 'canrx': 0x7ec, 'cantx': 0x7e4, 'autopad': True,
            'fields': (
                {'padding': 2},                                                     # _,_
                {'name': 'batteryInletTemperature', 'width': 1, 'offset': -40},     # A
                )
         },
        {'cmd': bytes.fromhex('2241A4'), 'canrx': 0x7ec, 'cantx': 0x7e4, 'autopad': True,
            'fields': (
                {'padding': 2},                                                     # _,_
                {'name': 'batteryInletTemperature', 'width': 1, 'offset': -40},     # A
                )
         },
        {'cmd': bytes.fromhex('22432d'), 'canrx': 0x7ec, 'cantx': 0x7e4, 'autopad': True,
            'fields': (
                {'padding': 2},                                                     # _,_
                {'name': 'dcBatteryVoltage', 'width': 2, 'scale': .52},             # A
                )
         },
        {'cmd': bytes.fromhex('224356'), 'canrx': 0x7ec, 'cantx': 0x7e4, 'autopad': True,
            'fields': (
                {'padding': 2},                                                     # _,_
                {'name': 'dcBatteryCurrent', 'width': 2, 'signed': True, 'scale': 1/(-6.675)},  # A # Scale ???
                )
         },
        {'cmd': bytes.fromhex('220042'), 'canrx': 0x7e8, 'cantx': 0x7e0, 'autopad': True,
            'fields': (
                {'padding': 2},                                                     # _,_
                {'name': 'auxBatteryVoltage', 'width': 2, 'scale': .001},             # A
                )
         },
        {'cmd': bytes.fromhex('224531'), 'canrx': 0x7ec, 'cantx': 0x7e4, 'autopad': True,
            'fields': (
                {'padding': 2},                                                     # _,_
                {'name': 'bmsBits', 'width': 1},                                    # A
                )
         },
        {'cmd': bytes.fromhex('220046'), 'canrx': 0x7e8, 'cantx': 0x7e0, 'autopad': True,
            'fields': (
                {'padding': 2},                                                     # _,_
                {'name': 'externalTemperature', 'width': 1, 'offset': -40},         # A
                )
         },
        {'computed': True,
            'fields': (
                {'name': 'dcBatteryPower',
                    'lambda': lambda d: d['dcBatteryCurrent'] * d['dcBatteryVoltage'] / 1000.0},
                {'name': 'charging',
                    'lambda': lambda d: int(d['bmsBits'] != 0)},
                {'name': 'normalChargePort',
                    'lambda': lambda d: int(d['bmsBits'] in (1, 2))},
                {'name': 'rapidChargePort',
                    'lambda': lambda d: int(d['bmsBits'] == 3)},
                )
         },
)


class IoniqBev(Car):
    """ Class for Checy Bolt """

    def __init__(self, config, dongle, watchdog, gps):
        Car.__init__(self, config, dongle, watchdog, gps)
        self._dongle.set_protocol('CAN_11_500')
        self._isotp = IsoTpDecoder(self._dongle, Fields)

    def read_dongle(self, data):
        """ Fetch data from CAN-bus and decode it.
            "data" needs to be a dictionary that will
            be modified with decoded data """

        data.update(self.get_base_data())
        data.update(self._isotp.get_data())

    def get_base_data(self):
        return {
            "CAPACITY": 28,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50.0
        }

    def get_abrp_model(self):
        return 'hyundai:ioniq:17:28:other'

    def get_evn_model(self):
        return 'IONIQ_BEV'
