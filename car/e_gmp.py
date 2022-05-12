""" Module for the Hyundai E-GMP platform """
# Based on https://www.dropbox.com/s/92oghj8s7dmgsia/TorqueIONIQ5AWD74kWh.csv?raw=1
from .car import Car, RollingAverage
from .isotp_decoder import IsoTpDecoder

Fields = (
    {'cmd': '220100', 'canrx': 0x7bb, 'cantx': 0x7b3, 'absolute': True, 'optional': True,
     'fields': [
         {'pos': 'f', 'name': 'externalTemperature', 'width': 1, 'scale': .5, 'offset': -40},
         {'pos': 'g', 'name': 'internalTemperature', 'width': 1, 'scale': .5, 'offset': -40},
         {'pos': 'ad', 'name': 'realVehicleSpeed', 'width': 1, 'scale': 1/3.6},     # km/h => m/s
         ]},
    {'cmd': '220101', 'canrx': 0x7ec, 'cantx': 0x7e4, 'absolute': True,
     'fields': [
         {'pos': 'e', 'name': 'SOC_BMS', 'width': 1, 'scale': .5},
         {'pos': 'j', 'name': 'charging_bits1', 'width': 1},
         {'pos': 'k', 'name': 'dcBatteryCurrent', 'width': 2, 'signed': True, 'scale': .1},
         {'pos': 'm', 'name': 'dcBatteryVoltage', 'width': 2, 'scale': .1},
         {'pos': 'o', 'name': 'batteryMaxTemperature', 'width': 1, 'signed': True},
         {'pos': 'p', 'name': 'batteryMinTemperature', 'width': 1, 'signed': True},
         {'pos': 'q', 'name': 'cellTemp%02d', 'idx': 1, 'cnt': 5, 'width': 1, 'signed': True},
         {'pos': 'x', 'name': 'maxCellVoltage', 'width': 1, 'scale': .02},
         {'pos': 'y', 'name': 'maxCellVoltNo', 'width': 1},
         {'pos': 'z', 'name': 'minCellVoltage', 'width': 1, 'scale': .02},
         {'pos': 'aa', 'name': 'minCellVoltNo', 'width': 1},
         {'pos': 'ad', 'name': 'auxBatteryVoltage', 'width': 1, 'scale': .1},
         {'pos': 'ae', 'name': 'cumulativeChargeCurrent', 'width': 4, 'scale': .1},
         {'pos': 'ai', 'name': 'cumulativeDischargeCurrent', 'width': 4, 'scale': .1},
         {'pos': 'am', 'name': 'cumulativeEnergyCharged', 'width': 4, 'scale': .1},
         {'pos': 'aq', 'name': 'cumulativeEnergyDischarged', 'width': 4, 'scale': .1},
         {'pos': 'au', 'name': 'operatingTime', 'width': 4},  # seconds
         {'pos': 'ay', 'name': 'charging_bits2', 'width': 1},
         {'pos': 'bb', 'name': 'driveMotorSpeed1', 'width': 2, 'signed': True},
         {'pos': 'bd', 'name': 'driveMotorSpeed2', 'width': 2, 'signed': True},
         ]},
    {'cmd': '220102', 'canrx': 0x7ec, 'cantx': 0x7e4, 'absolute': True,
     'fields': [
         {'pos': 'e', 'name': 'cellVoltage%03d', 'idx': 1, 'cnt': 32, 'width': 1, 'scale': .02},
         ]},
    {'cmd': '220103', 'canrx': 0x7ec, 'cantx': 0x7e4, 'absolute': True,
     'fields': [
         {'pos': 'e', 'name': 'cellVoltage%03d', 'idx': 33, 'cnt': 32, 'width': 1, 'scale': .02},
         ]},
    {'cmd': '220104', 'canrx': 0x7ec, 'cantx': 0x7e4, 'absolute': True,
     'fields': [
         {'pos': 'e', 'name': 'cellVoltage%03d', 'idx': 65, 'cnt': 32, 'width': 1, 'scale': .02},
         ]},
    {'cmd': '220105', 'canrx': 0x7ec, 'cantx': 0x7e4, 'absolute': True,
     'fields': [
         {'pos': 'j', 'name': 'cellTemp%02d', 'idx': 6, 'cnt': 7, 'width': 1, 'signed': True},
         {'pos': 'x', 'name': 'batteryInletTemperature', 'width': 1, 'signed': True},
         {'pos': 'z', 'name': 'soh', 'width': 2, 'scale': .1},
         {'pos': 'ab', 'name': 'maxCellDetNo', 'width': 1},
         {'pos': 'ac', 'name': 'minDeterioration', 'width': 2, 'scale': .1},
         {'pos': 'ae', 'name': 'minCellDetNo', 'width': 1},
         {'pos': 'af', 'name': 'SOC_DISPLAY', 'width': 1, 'scale': .5},
         {'pos': 'an', 'name': 'cellTemp%02d', 'idx': 13, 'cnt': 4, 'width': 1, 'signed': True},
         ]},
    {'cmd': '22010a', 'canrx': 0x7ec, 'cantx': 0x7e4, 'absolute': True,
     'fields': [
         {'pos': 'e', 'name': 'cellVoltage%03d', 'idx': 97, 'cnt': 32, 'width': 1, 'scale': .02},
         ]},
    {'cmd': '22010b', 'canrx': 0x7ec, 'cantx': 0x7e4, 'absolute': True,
     'fields': [
         {'pos': 'e', 'name': 'cellVoltage%03d', 'idx': 129, 'cnt': 32, 'width': 1, 'scale': .02},
         ]},
    {'cmd': '22010c', 'canrx': 0x7ec, 'cantx': 0x7e4, 'absolute': True,
     'fields': [
         {'pos': 'e', 'name': 'cellVoltage%03d', 'idx': 161, 'cnt': 32, 'width': 1, 'scale': .02},
         ]},
    {'cmd': '22b002', 'canrx': 0x7ce, 'cantx': 0x7c6, 'optional': True, 'absolute': True,
     'fields': [
         {'pos': 'g', 'name': 'odo', 'width': 3},
         ]},
    {'cmd': '22c00b', 'canrx': 0x7a8, 'cantx': 0x7a0, 'optional': True, 'absolute': True,
     'fields': [
         {'pos': 'e', 'name': 'tire_fl_pres', 'width': 1, 'scale': 0.2/14.504},
         {'pos': 'f', 'name': 'tire_fl_temp', 'width': 1, 'offset': -50},
         {'pos': 'j', 'name': 'tire_fr_pres', 'width': 1, 'scale': 0.2/14.504},
         {'pos': 'k', 'name': 'tire_fr_temp', 'width': 1, 'offset': -50},
         {'pos': 'o', 'name': 'tire_rl_pres', 'width': 1, 'scale': 0.2/14.504},
         {'pos': 'p', 'name': 'tire_rl_temp', 'width': 1, 'offset': -50},
         {'pos': 't', 'name': 'tire_rr_pres', 'width': 1, 'scale': 0.2/14.504},
         {'pos': 'u', 'name': 'tire_rr_temp', 'width': 1, 'offset': -50},
         ]},
    {'computed': True,
     'fields': (
         {'name': 'dcBatteryPower',
          'lambda': lambda d: d['dcBatteryCurrent'] * d['dcBatteryVoltage'] / 1000.0},
         {'name': 'normalChargePort',
          'lambda': lambda d: int(d['charging_bits1'] & 0x10 != 0)},
         {'name': 'rapidChargePort',
          'lambda': lambda d: int(d['charging_bits1'] & (0x10 | 0x20) != 0)},
         {'name': 'charging',
          'lambda': lambda d: d['normalChargePort'] or d['rapidChargePort']},
     )
     },
)


class E_GMP(Car):
    """ Decoder class for Hyundai E-GMP """

    def __init__(self, config, dongle, watchdog, gps):
        Car.__init__(self, config, dongle, watchdog, gps)
        self._dongle.set_protocol('CAN_11_500')
        self._isotp = IsoTpDecoder(self._dongle, Fields)
        self._avg_wheel_speed = RollingAverage(int(600/max(1, self._poll_interval)))
        self._avg_gps_speed = RollingAverage(int(600/max(1, self._poll_interval)))
        self._speed_factor = 1.0275

    def read_dongle(self, data):
        """ Read and parse data from dongle """
        data.update(self.get_base_data())
        data.update(self._isotp.get_data())

        temp_sum = 0
        temp_cnt = 0
        for i in range(1, 17):
            temp = data['cellTemp%02d' % i]
            temp_cnt = i
            if temp > 0:
                temp_sum += temp
            else:
                break

        data['batteryAvgTemperature'] = temp_sum / temp_cnt
        data['realVehicleSpeed'] *= self._speed_factor

        fix = self._gps.fix()
        if (fix and fix['mode'] > 1 and fix['hdop'] < 1 and 'speed' in fix and 
            speed - 10 < fix['speed'] < speed + 10):
            self._avg_gps_speed.push(fix['speed'])
            self._avg_wheel_speed.push(speed)
       
        gps_avg = self._avg_gps_speed.get()
        wheel_avg = self._avg_wheel_speed.get()
        if gps_avg and wheel_avg:
            #self._speed_factor *= gps_avg / wheel_avg
            data['_speed_factor'] = gps_avg / wheel_avg

        data['charging'] = 1 if (data['dcBatteryPower'] is not None and data['dcBatteryPower'] < -1.3) and data['realVehicleSpeed'] < 1 else 0  # 1.3kW is lowest possible charging rate (6A single phase at 230V)

    def get_base_data(self):
        return {
            "CAPACITY": 64,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50.0
        }

    def get_evn_model(self):
        return 'E-GMP'
