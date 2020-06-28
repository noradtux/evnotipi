from .car import *

B220100 = bytes.fromhex('220100')
B220101 = bytes.fromhex('220101')
B220102 = bytes.fromhex('220102')
B220103 = bytes.fromhex('220103')
B220104 = bytes.fromhex('220104')
B220105 = bytes.fromhex('220105')
B22b002 = bytes.fromhex('22b002')

class KONA_EV(Car):

    def __init__(self, config, dongle, watchdog, gps):
        Car.__init__(self, config, dongle, watchdog, gps)
        self.dongle.setProtocol('CAN_11_500')

    def readDongle(self, data):
        now = time()
        raw = {}

        for cmd in [B220101, B220102, B220103, B220104, B220105]:
            raw[cmd] = self.dongle.sendCommandEx(cmd, canrx=0x7ec, cantx=0x7e4)

        try:
            raw[B22b002] = self.dongle.sendCommandEx(B22b002, canrx=0x7ce, cantx=0x7c6)
        except NoData:
            # 0x7ce is only available while driving
            pass

        data.update(self.getBaseData())

        charging_bits = raw[B220101][53]
        dc_battery_current = ifbs(raw[B220101][13:15]) / 10.0
        dc_battery_voltage = ifbu(raw[B220101][15:17]) / 10.0

        cell_temps = [
            ifbs(raw[B220101][19:20]),
            ifbs(raw[B220101][20:21]),
            ifbs(raw[B220101][21:22]),
            ifbs(raw[B220101][22:23])]

        cell_voltages = []
        for cmd in [B220102, B220103]:
            for byte in range(7, 39):
                cell_voltages.append(raw[cmd][byte] / 50.0)

        for byte in range(7, 31):
            cell_voltages.append(raw[B220104][byte] / 50.0)

        data.update({
            # Base:
            'SOC_BMS':                  raw[B220101][7] / 2.0,
            'SOC_DISPLAY':              raw[B220105][34] / 2.0,
            # Extended:
            'auxBatteryVoltage':        raw[B220101][32] / 10.0,
            'batteryInletTemperature':  ifbs(raw[B220101][25:26]),
            'batteryMaxTemperature':    ifbs(raw[B220101][17:18]),
            'batteryMinTemperature':    ifbs(raw[B220101][18:19]),
            'cumulativeEnergyCharged':  ifbu(raw[B220101][41:45]) / 10.0,
            'cumulativeEnergyDischarged': ifbu(raw[B220101][45:49]) / 10.0,
            'charging':                 1 if (charging_bits & 0xc) == 0x8 else 0,
            'normalChargePort':         1 if (charging_bits & 0x80) and raw[B220101][12] == 3 else 0,
            'rapidChargePort':          1 if (charging_bits & 0x80) and raw[B220101][12] != 3 else 0,
            'dcBatteryCurrent':         dc_battery_current,
            'dcBatteryPower':           dc_battery_current * dc_battery_voltage / 1000.0,
            'dcBatteryVoltage':         dc_battery_voltage,
            'soh':                      ifbu(raw[B220105][28:30]) / 10.0,
            #'externalTemperature':      (raw[B220100][0x7ce][1][3] - 80) / 2.0,
            'odo':                      ffbu(raw[B22b002][9:12]) if B22b002 in raw else None,
            })

        for i, temp in enumerate(cell_temps):
            key = "cellTemp{:02d}".format(i+1)
            data[key] = float(temp)

        for i, cvolt in enumerate(cell_voltages):
            key = "cellVoltage{:02d}".format(i+1)
            data[key] = float(cvolt)

    def getBaseData(self):
        return {
            "CAPACITY": 64,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50.0
        }
