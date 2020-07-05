""" Decoder for the Hyundai Kona and friends """

from .car import Car
from .isotp_decoder import IsoTpDecoder

B220100 = bytes.fromhex('220100')
B220101 = bytes.fromhex('220101')
B220102 = bytes.fromhex('220102')
B220103 = bytes.fromhex('220103')
B220104 = bytes.fromhex('220104')
B220105 = bytes.fromhex('220105')
B22b002 = bytes.fromhex('22b002')

Fields = {
    B220101: {'canrx': 0x7ec, 'cantx': 0x7e4,
              'fields': (
                  {'format': '7x'}, # 7 bytes padding
                  {'name': 'SOC_BMS', 'format': 'B', 'scale': .5},
                  {'format': '4x'}, # 4 bytes padding
                  {'name': 'charging_bits1', 'format': 'B'},
                  {'name': 'dcBatteryCurrent', 'format': 'h', 'scale': .1},
                  {'name': 'dcBatteryVoltage', 'format': 'H', 'scale': .1},
                  {'name': 'batteryMaxTemperature', 'format': 'b'},
                  {'name': 'batteryMinTemperature', 'format': 'b'},
                  {'name': 'cellTemp{:02d}', 'idx': 1, 'cnt': 4, 'format': 'b'},
                  {'format': '2x'}, # 2 bytes padding
                  {'name': 'batteryInletTemperature', 'format': 'b'},
                  {'format': '6x'}, # 6 bytes padding
                  {'name': 'auxBatteryVoltage', 'format': 'B', 'scale': .1},
                  {'name': 'cumulativeChargeCurrent', 'format': 'L', 'scale': .1},
                  {'name': 'cumulativeDischargeCurrent', 'format': 'L', 'scale': .1},
                  {'name': 'cumulativeEnergyCharged', 'format': 'L', 'scale': .1},
                  {'name': 'cumulativeEnergyDischarged', 'format': 'L', 'scale': .1},
                  {'name': 'operatingTime', 'format': 'L'}, # seconds
                  {'name': 'charging_bits2', 'format': 'B'},
                  {'format': '8x'}, # 8 bytes padding
                  )
             },
    B220102: {'canrx': 0x7ec, 'cantx': 0x7e4,
              'fields': (
                  {'format': '6x'}, # 7 bytes padding
                  {'name': 'cellVoltage{:02d}', 'idx': 1, 'cnt': 32, 'format': 'B', 'scale': .02},
                  {'format': 'x'}, # one byte padding
                  )
             },
    B220103: {'canrx': 0x7ec, 'cantx': 0x7e4,
              'fields': (
                  {'format': '6x'}, # 7 bytes padding
                  {'name': 'cellVoltage{:02d}', 'idx': 33, 'cnt': 32, 'format': 'B', 'scale': .02},
                  {'format': 'x'}, # one byte padding
                  )
             },
    B220104: {'canrx': 0x7ec, 'cantx': 0x7e4,
              'fields': (
                  {'format': '6x'}, # 7 bytes padding
                  {'name': 'cellVoltage{:02d}', 'idx': 65, 'cnt': 32, 'format': 'B', 'scale': .02},
                  {'format': 'x'}, # one byte padding
                  )
             },
    B220105: {'canrx': 0x7ec, 'cantx': 0x7e4,
              'fields': (
                  {'format': '28x'}, # 28 bytes padding
                  {'name': 'soh', 'format': 'H', 'scale': .1},
                  {'format': '4x'}, # 4 bytes padding
                  {'name': 'SOC_DISPLAY', 'format': 'B', 'scale': .5},
                  {'format': '11x'}, # 11 bytes padding
                  )
             },
    B22b002: {'canrx': 0x7ce, 'cantx': 0x7c6, 'optional': True,
              'fields': (
                  {'format': '9x'},
                  {'name': 'odo', 'format': 'BH', 'lambda': lambda o: o[0]<<16 | o[1]},
                  {'format': '3x'},
                  )
             },
    }

class KONA_EV(Car):
    """ Decoder Class for Kona """

    def __init__(self, config, dongle, watchdog, gps):
        Car.__init__(self, config, dongle, watchdog, gps)
        self.dongle.setProtocol('CAN_11_500')
        self._isotp = IsoTpDecoder(self.dongle, Fields)

    def readDongle(self, data):

        data.update(self.getBaseData())
        data.update(self._isotp.get_data())
        charging_bits1 = data['charging_bits1']
        charging_bits2 = data['charging_bits2']
        data.update({
            'dcBatteryPower': data['dcBatteryCurrent'] * data['dcBatteryVoltage'] / 1000.0,
            'charging':                 1 if (charging_bits2 & 0xc) == 0x8 else 0,
            'normalChargePort':         1 if (charging_bits2 & 0x80) and charging_bits1 == 3 else 0,
            'rapidChargePort':          1 if (charging_bits2 & 0x80) and charging_bits1 != 3 else 0,
            })

    def getBaseData(self):
        return {
            "CAPACITY": 64,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50.0
        }
