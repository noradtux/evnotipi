""" Decoder for the Hyundai Ioniq EV 28kWh """

from .car import Car
from .isotp_decoder import IsoTpDecoder

B2101 = bytes.fromhex('2101')
B2102 = bytes.fromhex('2102')
B2103 = bytes.fromhex('2103')
B2104 = bytes.fromhex('2104')
B2105 = bytes.fromhex('2105')
B2180 = bytes.fromhex('2180')
B22b002 = bytes.fromhex('22b002')

Fields = {
    B2101: {'canrx': 0x7ec, 'cantx': 0x7e4,
            'fields': (
                {'format': '6x'},
                {'name': 'SOC_BMS', 'format': 'B', 'scale': .5},
                {'name': 'availableChargePower', 'format': 'H', 'scale': .01},
                {'name': 'availableDischargePower', 'format': 'H', 'scale': .01},
                {'name': 'charging_bits', 'format': 'B'},
                {'name': 'dcBatteryCurrent', 'format': 'h', 'scale': .1},
                {'name': 'dcBatteryVoltage', 'format': 'H', 'scale': .1},
                {'name': 'batteryMaxTemperature', 'format': 'b'},
                {'name': 'batteryMinTemperature', 'format': 'b'},
                {'name': 'cellTemp%02d', 'idx': 1, 'cnt': 5, 'format': 'b'},
                {'format': 'x'},
                {'name': 'batteryInletTemperature', 'format': 'b'},
                {'format': '4x'},
                {'name': 'fanStatus', 'format': 'B'},
                {'name': 'fanFeedback', 'format': 'B'},
                {'name': 'auxBatteryVoltage', 'format': 'B', 'scale': .1},
                {'name': 'cumulativeChargeCurrent', 'format': 'L', 'scale': .1},
                {'name': 'cumulativeDischargeCurrent', 'format': 'L', 'scale': .1},
                {'name': 'cumulativeEnergyCharged', 'format': 'L', 'scale': .01},
                {'name': 'cumulativeEnergyDischarged', 'format': 'L', 'scale': .01},
                {'name': 'operatingTime', 'format': 'L'}, # seconds
                {'format': '3x'},
                {'name': 'driveMotorSpeed', 'format': 'h', 'offset': 0, 'scale': 1},
                {'format': '4x'},
                # Len: 56
                )
            },
    B2102: {'canrx': 0x7ec, 'cantx': 0x7e4,
            'fields': (
                {'format': '6x'},
                {'name': 'cellVoltage%02d', 'idx': 1, 'cnt': 32, 'format': 'B', 'scale': .02},
                # Len: 38
                )
            },
    B2103: {'canrx': 0x7ec, 'cantx': 0x7e4,
            'fields': (
                {'format': '6x'},
                {'name': 'cellVoltage%02d', 'idx': 33, 'cnt': 32, 'format': 'B', 'scale': .02},
                # Len: 38
                )
            },
    B2104: {'canrx': 0x7ec, 'cantx': 0x7e4,
            'fields': (
                {'format': '6x'},
                {'name': 'cellVoltage%02d', 'idx': 65, 'cnt': 32, 'format': 'B', 'scale': .02},
                # Len: 38
                )
            },
    B2105: {'canrx': 0x7ec, 'cantx': 0x7e4,
            'fields': (
                {'format': '11x'},
                {'name': 'cellTemp%02d', 'idx': 6, 'cnt': 7, 'format': 'b'},
                {'format': '9x'},
                {'name': 'soh', 'format': 'H', 'scale': .1},
                {'format': '4x'},
                {'name': 'SOC_DISPLAY', 'format': 'B', 'scale': .5},
                {'format': '11x'},
                # Len: 45
                )
            },
    B2180: {'canrx': 0x7ee, 'cantx': 0x7e6,
            'fields': (
                {'format': '14x'},
                {'name': 'externalTemperature', 'format': 'B', 'scale': .5, 'offset': -40},
                {'format': '10x'},
                # Len: 25
                )
            },
    B22b002: {'canrx': 0x7ce, 'cantx': 0x7c6, 'optional': True,
              'fields': (
                  {'format': '9x'},
                  {'name': 'odo', 'format': 'BH', 'lambda': lambda o: o[0]<<16 | o[1]},
                  {'format': '3x'},
                  # Len: 15
                  )
              },
    'CALC': {'computed': True,
             'fields': (
                 {'name': 'dcBatteryPower', 'lambda': lambda d: d['dcBatteryCurrent'] * d['dcBatteryVoltage'] / 1000.0},
                 {'name': 'charging', 'lambda': lambda d: int(d['charging_bits'] & 0x80)},
                 {'name': 'normalChargePort', 'lambda': lambda d: int(d['charging_bits'] & 0x20)},
                 {'name': 'rapidChargePort', 'lambda': lambda d: int(d['charging_bits'] & 0x40)},
                 )
             },
    }

class IONIQ_BEV(Car):
    """ Decoder class for Ioniq EV """

    def __init__(self, config, dongle, watchdog, gps):
        Car.__init__(self, config, dongle, watchdog, gps)
        self.dongle.setProtocol('CAN_11_500')
        self._isotp = IsoTpDecoder(self.dongle, Fields)

    def readDongle(self, data):
        """ Fetch data from CAN-bus and decode it.
            "data" needs to be a dictionary that will
            be modified with decoded data """

        data.update(self.getBaseData())
        data.update(self._isotp.get_data())

        #'batteryAvgTemperature':    sum(cell_temps) / len(cell_temps),

    def getBaseData(self):
        return {
            "CAPACITY": 28,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50.0
        }

    def getABRPModel(self):
        return 'hyundai:ioniq:17:28:other'

    def getEVNModel(self):
        return 'IONIQ_BEV'

