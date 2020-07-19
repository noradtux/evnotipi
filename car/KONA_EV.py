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

Fields = (
    {'cmd': B220101, 'canrx': 0x7ec, 'cantx': 0x7e4,
     'fields': (
         {'padding': 7},
         {'name': 'SOC_BMS', 'width': 1, 'scale': .5},
         {'padding': 4},
         {'name': 'charging_bits1', 'width': 1},
         {'name': 'dcBatteryCurrent', 'width': 2, 'signed': True, 'scale': .1},
         {'name': 'dcBatteryVoltage', 'width': 2, 'scale': .1},
         {'name': 'batteryMaxTemperature', 'width': 1, 'signed': True},
         {'name': 'batteryMinTemperature', 'width': 1, 'signed': True},
         {'name': 'cellTemp%02d', 'idx': 1, 'cnt': 4, 'width': 1, 'signed': True},
         {'padding': 2},
         {'name': 'batteryInletTemperature', 'width': 1, 'signed': True},
         {'padding': 6},
         {'name': 'auxBatteryVoltage', 'width': 1, 'scale': .1},
         {'name': 'cumulativeChargeCurrent', 'width': 4, 'scale': .1},
         {'name': 'cumulativeDischargeCurrent', 'width': 4, 'scale': .1},
         {'name': 'cumulativeEnergyCharged', 'width': 4, 'scale': .1},
         {'name': 'cumulativeEnergyDischarged', 'width': 4, 'scale': .1},
         {'name': 'operatingTime', 'width': 4}, # seconds
         {'name': 'charging_bits2', 'width': 1},
         {'padding': 8},
         )
    },
    {'cmd': B220102, 'canrx': 0x7ec, 'cantx': 0x7e4,
     'fields': (
         {'padding': 7},
         {'name': 'cellVoltage%02d', 'idx': 1, 'cnt': 32, 'width': 1, 'scale': .02},
         )
    },
    {'cmd': B220103, 'canrx': 0x7ec, 'cantx': 0x7e4,
     'fields': (
         {'padding': 7},
         {'name': 'cellVoltage%02d', 'idx': 33, 'cnt': 32, 'width': 1, 'scale': .02},
         )
    },
    {'cmd': B220104, 'canrx': 0x7ec, 'cantx': 0x7e4,
     'fields': (
         {'padding': 7},
         {'name': 'cellVoltage%02d', 'idx': 65, 'cnt': 32, 'width': 1, 'scale': .02},
         )
    },
    {'cmd': B220105, 'canrx': 0x7ec, 'cantx': 0x7e4,
     'fields': (
         {'padding': 28},
         {'name': 'soh', 'width': 2, 'scale': .1},
         {'padding': 4},
         {'name': 'SOC_DISPLAY', 'width': 1, 'scale': .5},
         {'padding': 11},
         )
    },
    {'cmd': B22b002, 'canrx': 0x7ce, 'cantx': 0x7c6, 'optional': True,
     'fields': (
         {'padding': 9},
         {'name': 'odo', 'width': 3},
         {'padding': 3},
         )
    },
    {'computed': True,
     'fields': (
         {'name': 'dcBatteryPower',
          'lambda': lambda d: d['dcBatteryCurrent'] * d['dcBatteryVoltage'] / 1000.0},
         {'name': 'charging',
          'lambda': lambda d: int(d['charging_bits2'] & 0xc == 0x8)},
         {'name': 'normalChargePort',
          'lambda': lambda d: int((d['charging_bits2'] & 0x80) != 0 and d['charging_bits1'] == 3)},
         {'name': 'rapidChargePort',
          'lambda': lambda d: int((d['charging_bits2'] & 0x80) != 0 and d['charging_bits1'] != 3)},
         )
    },
    )

class KONA_EV(Car):
    """ Decoder Class for Kona """

    def __init__(self, config, dongle, watchdog, gps):
        Car.__init__(self, config, dongle, watchdog, gps)
        self.dongle.setProtocol('CAN_11_500')
        self._isotp = IsoTpDecoder(self.dongle, Fields)

    def readDongle(self, data):
        data.update(self.getBaseData())
        data.update(self._isotp.get_data())

    def getBaseData(self):
        return {
            "CAPACITY": 64,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50.0
        }
