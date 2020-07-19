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

Fields = (
    {'cmd': B2101, 'canrx': 0x7ec, 'cantx': 0x7e4,
     'fields': (
         {'padding': 6},
         {'name': 'SOC_BMS', 'width': 1, 'scale': .5},
         {'name': 'availableChargePower', 'width': 2, 'scale': .01},
         {'name': 'availableDischargePower', 'width': 2, 'scale': .01},
         {'name': 'charging_bits', 'width': 1},
         {'name': 'dcBatteryCurrent', 'width': 2, 'signed': True, 'scale': .1},
         {'name': 'dcBatteryVoltage', 'width': 2, 'scale': .1},
         {'name': 'batteryMaxTemperature', 'width': 1, 'signed': True},
         {'name': 'batteryMinTemperature', 'width': 1, 'signed': True},
         {'name': 'cellTemp%02d', 'idx': 1, 'cnt': 5,
          'width': 1, 'signed': True},
         {'padding': 1},
         {'name': 'batteryInletTemperature', 'width': 1, 'signed': True},
         {'padding': 4},
         {'name': 'fanStatus', 'width': 1},
         {'name': 'fanFeedback', 'width': 1},
         {'name': 'auxBatteryVoltage', 'width': 1, 'scale': .1},
         {'name': 'cumulativeChargeCurrent', 'width': 4, 'scale': .1},
         {'name': 'cumulativeDischargeCurrent', 'width': 4, 'scale': .1},
         {'name': 'cumulativeEnergyCharged', 'width': 4, 'scale': .01},
         {'name': 'cumulativeEnergyDischarged', 'width': 4, 'scale': .01},
         {'name': 'operatingTime', 'width': 4}, # seconds
         {'padding': 3},
         {'name': 'driveMotorSpeed', 'width': 2, 'signed': True,
          'offset': 0, 'scale': 1},
         {'padding': 4},
         # Len: 56
         )
    },
    {'cmd': B2102, 'canrx': 0x7ec, 'cantx': 0x7e4,
     'fields': (
         {'padding': 6},
         {'name': 'cellVoltage%02d', 'idx': 1, 'cnt': 32, 'width': 1, 'scale': .02},
         # Len: 38
         )
    },
    {'cmd': B2103, 'canrx': 0x7ec, 'cantx': 0x7e4,
     'fields': (
         {'padding': 6},
         {'name': 'cellVoltage%02d', 'idx': 33, 'cnt': 32, 'width': 1, 'scale': .02},
         # Len: 38
         )
    },
    {'cmd': B2104, 'canrx': 0x7ec, 'cantx': 0x7e4,
     'fields': (
         {'padding': 6},
         {'name': 'cellVoltage%02d', 'idx': 65, 'cnt': 32, 'width': 1, 'scale': .02},
         # Len: 38
         )
    },
    {'cmd': B2105, 'canrx': 0x7ec, 'cantx': 0x7e4,
     'fields': (
         {'padding': 11},
         {'name': 'cellTemp%02d', 'idx': 6, 'cnt': 7, 'width': 1, 'signed': True},
         {'padding': 9},
         {'name': 'soh', 'width': 2, 'scale': .1},
         {'padding': 4},
         {'name': 'SOC_DISPLAY', 'width': 1, 'scale': .5},
         {'padding': 11},
         # Len: 45
         )
    },
    {'cmd': B2180, 'canrx': 0x7ee, 'cantx': 0x7e6,
     'fields': (
         {'padding': 14},
         {'name': 'externalTemperature', 'width': 1, 'scale': .5, 'offset': -40},
         {'padding': 10},
         # Len: 25
         )
    },
    {'cmd': B22b002, 'canrx': 0x7ce, 'cantx': 0x7c6, 'optional': True,
     'fields': (
         {'padding': 9},
         {'name': 'odo', 'width': 3},
         {'padding': 3},
         # Len: 15
         )
    },
    {'computed': True,
     'fields': (
         {'name': 'dcBatteryPower', 'lambda': lambda d: d['dcBatteryCurrent'] *
                                              d['dcBatteryVoltage'] / 1000.0},
         {'name': 'charging', 'lambda': lambda d: int(d['charging_bits'] & 0x80 != 0)},
         {'name': 'normalChargePort', 'lambda': lambda d: int(d['charging_bits'] & 0x20 != 0)},
         {'name': 'rapidChargePort', 'lambda': lambda d: int(d['charging_bits'] & 0x40 != 0)},
         )
    },
    )

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

