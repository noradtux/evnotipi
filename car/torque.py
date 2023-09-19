#!/usr/bin/env python3

from time import time, sleep
import re
from .car import Car


def var_to_offset(var: str):
    """ convert a Torque-style offset (a - zz) to a numeric offset """
    var_len = len(var)
    assert var_len <= 2
    var = var.lower()
    ord_a = 97
    ord_z = 122
    offset = 2  # 'a' is at position 2 of the block
    for idx, val in enumerate(var):
        char = ord(val)
        assert ord_a <= char <= ord_z

        if var_len - idx > 1:
            offset += (char - ord_a + 1) * 25 + 1
        else:
            offset += char - ord_a

    return offset


def parse_formula(formula: str):
    """ parses a Torque-style formula into a Python expression """
    # p: parsed data
    # r: raw input
    expression = 'lambda p,r: '
    idx = 0
    input_length = len(formula)
    while idx < input_length:
        token = formula[idx].lower()

        if '0' <= token <= '9':
            expression += token

        elif token in ['<', '>']:
            expression += token * 2

        elif token in ['(', ')', '+', '-', '*', '/', '.']:
            expression += token

        elif token == 's' and formula[idx:idx+6].lower() == 'signed':
            idx += 6
            idx = formula.find('(', idx)
            assert idx != -1
            idx += 1
            var_start = idx
            idx = formula.find(')', idx)
            assert idx != -1
            offset = var_to_offset(formula[var_start:idx])
            expression += "int.from_bytes(r[%i], byteorder='big', signed=True)" % offset

        elif token == 'v' and formula[idx:idx+3].lower() == 'val':
            idx += 3
            idx = formula.find('{', idx)
            assert idx != -1
            idx += 1
            var_start = idx
            idx = formula.find('}', idx)
            assert idx != -1
            var = formula[var_start:idx]
            if re.match('^[a-zA-Z0-9_ ]+$', var) is None:
                raise ValueError()

            expression += "p['%s']" % var

        elif token == 'i' and formula[idx:idx+3].lower() == 'int':
            idx += 3
            bits = int(formula[idx:idx+2])
            assert(bits % 8 == 0)
            idx = formula.find('(', idx)
            assert idx != -1
            idx += 1
            end_idx = formula.find(')', idx)
            assert end_idx != -1
            vrs = formula[idx:end_idx].split(':')
            expression += '('
            for i in range(0, int(bits/8)):
                if i != 0:
                    expression += '+'
                expression += "(r['%s']<<%i)" % (var_to_offset(vrs[i]), bits-(i+1)*8)
            expression += ')'
            idx = end_idx

        elif 'a' <= token <= 'z':
            var = token
            while idx+1 < input_length and 'a' <= formula[idx+1].lower() <= 'z':
                idx += 1
                var += formula[idx]

            expression += "r[%i]" % var_to_offset(var)

        elif token == '{':
            idx += 1
            end_idx = formula.find('}', idx)
            assert end_idx != -1

            var, bit = formula[idx:end_idx].split(':')

            expression += 'int((r[%i] & (1 << %i))!=0)' % (var_to_offset(var), int(bit))

            idx = end_idx

        idx += 1

    return expression


class TorqueCsv(Car):
    """ Class for vehicle definition based on Torque style CSV files """

    def __init__(self, config, dongle, watchdog, gps):
        Car.__init__(self, config, dongle, watchdog, gps)
        self._dongle.set_protocol('CAN_11_500')
        self._fields = {}
        self._evn_car_type = None
        self._evn_base_data = None


    def load_csv_from_file(self, file_name):
        with open(file_name, 'r') as f:
            for line in f:
                fields = re.split(r'\s*[;,]\s*', line.strip())
                name = str(fields[0])
                # 'disp_name': str(fields[1])
                cmd = bytes.fromhex(fields[2])
                formula_str = parse_formula(str(fields[3]))
                formula = eval(formula_str)
                # 'min': float(fields[4])
                # 'max': float(fields[5])
                # 'unit': str(fields[6])
                cantx = int(fields[7], 16)
                canrx = int(fields[8], 16) if len(fields) == 9 else int(fields[7], 16) + 8

                if cantx not in self._fields:
                    self._fields[cantx] = {'canrx': canrx, 'cmd': {}}
                if cmd not in self._fields[cantx]['cmd']:
                    self._fields[cantx]['cmd'][cmd] = {}

                self._fields[cantx]['cmd'][cmd][name] = {
                        'formula': formula,
                        'formula_str': formula_str
                        }

    def read_dongle(self, data):
        """ Fetch data from CAN-bus and decode it.
            "data" needs to be a dictionary that will
            be modified with decoded data """

        data.update(self.get_base_data())
        for cantx, can_field in self._fields:
            canrx = can_field['canrx']
            for cmd, cmd_field in can_field['cmd']:
                raw = self._dongle.send_command_ex(cmd, canrx=canrx, cantx=cantx)
                for name, name_field in cmd_field:
                    data[name] = name_field['formula'](data, raw)

    def get_base_data(self):
        return self._evn_base_data

    def get_abrp_model(self):
        return None

    def get_evn_model(self):
        return self._evn_car_type


if __name__ == "__main__":
    pass
