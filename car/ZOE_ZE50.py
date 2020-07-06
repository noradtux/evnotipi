""" Decoder for the Renault Zoe Z.E.50 """

from .car import *
from .isotp_decoder import IsoTpDecoder

CMD_AUX_VOLTAGE = bytes.fromhex('222005')  # EVC
CMD_CHARGE_STATE = bytes.fromhex('225017')  # BCB 0:Nok;1:AC mono;2:AC tri;3:DC;4:AC bi
CMD_SOC = bytes.fromhex('222002')  # EVC
CMD_SOC_BMS = bytes.fromhex('229002')  # LBC
CMD_VOLTAGE = bytes.fromhex('229006')
CMD_BMS_ENERGY = bytes.fromhex('2291C8')  # PR155
CMD_ODO = bytes.fromhex('222006')  # EVC
CMD_NRG_DISCHARG = bytes.fromhex('229245')  # PR047
CMD_CURRENT = bytes.fromhex('223204')  # EVC <<- BROKEN
CMD_SOH = bytes.fromhex('223206')  # EVC

Fields = {
    CMD_AUX_VOLTAGE: {'canrx': 0x18daf1da, 'cantx': 0x18dadaf1,
        'fields': (
            {'format': '3x'}, # 3 bytes padding
            {'name': 'auxBatteryVoltage', 'format': 'B', 'scale': .01},
            )
        },
    CMD_CHARGE_STATE: {'canrx': 0x18daf1de, 'cantx': 0x18daf1de,
        'fields': (
            {'format': '3x'}, # 3 bytes padding
            {'name': 'charge_state', 'format': 'B'},
            )
        },
    CMD_SOC: {'canrx': 0x18daf1da, 'cantx': 0x18dadaf1,
        'fields': (
            {'format': '3x'}, # 3 bytes padding
            {'name': 'SOC_DISPLAY', 'format': 'B', 'scale': .02},
            )
        },
    CMD_SOC_BMS: {'canrx': 0x18daf1db, 'cantx': 0x18dadbf1,
        'fields': (
            {'format': '3x'}, # 3 bytes padding
            {'name': 'SOC_BMS', 'format': 'B', 'scale': .01},
            )
        },
    CMD_VOLTAGE: {'canrx': 0x18daf1db, 'cantx': 0x18dadbf1,
        'fields': (
            {'format': '3x'}, # 3 bytes padding
            {'name': 'dcBatteryVoltage', 'format': 'B', 'scale': .001},
            )
        },
    CMD_BMS_ENERGY: {'canrx': 0x18daf1db, 'cantx': 0x18dadbf1,
        'fields': (
            {'format': '3x'}, # 3 bytes padding
            {'name': 'cumulativeEnergyCharged', 'format': 'B', 'scale': .001},
            )
        },
    CMD_ODO: {'canrx': 0x18daf1da, 'cantx': 0x18dadaf1,
        'fields': (
            {'format': '3x'}, # 3 bytes padding
            {'name': 'odo', 'format': 'H'},
            )
        },
    CMD_NRG_DISCHARG: {'canrx': 0x18daf1db, 'cantx': 0x18dadbf1,
        'fields': (
            {'format': '3x'}, # 3 bytes padding
            {'name': 'cumulativeEnergyDischarged', 'format': 'B', 'scale': .001},
            )
        },
    CMD_CURRENT: {'canrx': 0x18daf1da, 'cantx': 0x18dadaf1,
        'fields': (
            {'format': '3x'}, # 3 bytes padding
            {'name': 'dcBatteryCurrent', 'format': 'B', 'scale': 1},
            )
        },
    #CMD_SOH: {'canrx': 0x18daf1da, 'cantx': 0x18dadaf1,
    #    'fields': (
    #        {'format': '3x'}, # 3 bytes padding
    #        {'name': 'soh', 'format': 'b'},
    #        )
    #    },
    }

class ZOE_ZE50(Car):
    def __init__(self, config, dongle, watchdog, gps):
        Car.__init__(self, config, dongle, watchdog, gps)
        self.dongle.setProtocol('CAN_29_500')

        idx = 1
        for i in range(0x21, 0x84):
            c = bytes.fromhex("2290%02x" % (i))
            Fields[c] = {'canrx': 0x18daf1db, 'cantx': 0x18dadbf1,
                    'fields': ({'format': '3x'},
                        {'name': 'cellVolt%02d' % (idx), 'format': 'B', 'scale': .001})
                    }
            idx += 1

        idx = 1
        for i in range(0x31, 0x3d):
            c = bytes.fromhex("2291%02x" % (i))
            Fields[c] = {'canrx': 0x18daf1db, 'cantx': 0x18dadbf1,
                    'fields': ({'format': '3x'},
                        {'name': 'cellTemp%02d' % (idx), 'format': 'B', 'scale': .1, 'offset': -60})
                    }
            idx += 1

        self._isotp = IsoTpDecoder(self.dongle, Fields)

    def readDongle(self, data):
        def lbc(cmd):   # Lithium Battery Controller
            return self.dongle.sendCommandEx(cmd, canrx=0x18daf1db, cantx=0x18dadbf1)[3:]
        def evc(cmd):   # Vehicle Controle Module
            return self.dongle.sendCommandEx(cmd, canrx=0x18daf1da, cantx=0x18dadaf1)[3:]
        def bcb(cmd):   # Battery Charger Block
            return self.dongle.sendCommandEx(cmd, canrx=0x18daf1de, cantx=0x18dadef1)[3:]

        data.update(self.getBaseData())
        data.update(self._isotp.get_data())

        charge_state = data['charge_state']

        data.update({
            #'batteryInletTemperature':
            #'batteryMaxTemperature': max(module_temps),
            #'batteryMinTemperature': min(module_temps),

            'charging':             int(charge_state != 0),
            'normalChargePort':     int(charge_state in (1, 2, 4)),
            'rapidChargePort':      int(charge_state == 3),

            'dcBatteryPower':       data['dcBatteryCurrent'] * data['dcBatteryVoltage'] / 1000.0,

            #'soh':                  100 - ifbu(evc(CMD_SOH)),
            #'externalTemperature':
            })

    def getBaseData(self):
        return {
            "CAPACITY": 50,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 22.0,
            "FAST_SPEED": 50.0
        }
