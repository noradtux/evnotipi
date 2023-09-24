""" Generic decoder for ISO-TP based cars """
import logging
import struct
from dongle import NoData

FormatMap = {
    0: {'f': 'x'},
    1: {'f': 'b'},
    2: {'f': 'h'},
    3: {'f': 'bh', 'l': lambda o: o[0] << 16 | o[1]},
    4: {'f': 'i'},
    8: {'f': 'l'},
}


def is_power_of_two(number):
    """ Check of argument has power of two """
    return (number & (number-1) == 0) and number != 0


TqBase = ord('a') - 1


def tq(pos: str) -> int:
    """ Convert Torque style address (a - zz) to an int """
    pos = pos.lower()
    if len(pos) == 1:
        return ord(pos) - TqBase + 3
    if len(pos) == 2:
        return ((ord(pos[0]) - TqBase) * 26 +
                ord(pos[1]) - TqBase) + 3
    raise ValueError()


class IsoTpDecoder:
    """ Generic decoder for ISO-TP based cars """

    def __init__(self, dongle, fields):
        self._log = logging.getLogger("EVNotiPi/ISO-TP-Decoder")
        self._dongle = dongle
        self._fields = fields

        self.preprocess_fields()

    def preprocess_fields(self):
        """ Preprocess field structure,
            creating format strings for unpack etc.,"""
        for cmd_data in self._fields:
            fmt = ">"
            fmt_idx = 0
            fmt_last_pos = 0

            if 'cmd' in cmd_data:
                if isinstance(cmd_data['cmd'], str):
                    cmd_data['cmd'] = bytes.fromhex(cmd_data['cmd'])
                elif not isinstance(cmd_data['cmd'], bytes):
                    raise ValueError('Expected bytes or str as cmd')

            # make sure 'computed' is set so we don't need to check for it
            # in the decoder. Checking is slow.
            cmd_data['computed'] = cmd_data.get('computed', False)
            cmd_data['simple'] = cmd_data.get('simple', False)
            absolute_mode = cmd_data.get('absolute', False)
            if absolute_mode:
                cmd_data['autopad'] = True

            if cmd_data.get('simple'):
                # simple mode is for platforms like MEB or Zoe ZE50 which return
                # one value per command. Padding and width will be auto-set
                assert len(cmd_data['fields']) == 1

                field = cmd_data['fields'][0]
                fmt += str(len(cmd_data['cmd'])) + 'x'
                field['simple'] = True
                field['scale'] = field.get('scale', 1)
                field['offset'] = field.get('offset', 0)
                field['fmt_idx'] = 0
                cmd_data['struct'] = struct.Struct(fmt)

            elif not cmd_data['computed']:
                # Build a new array instead of inserting into the existing one.
                # Should be quicker.
                if absolute_mode:
                    for field in cmd_data['fields']:
                        if isinstance(field['pos'], str):
                            field['pos'] = tq(field['pos'])

                    fields = sorted(cmd_data['fields'],
                                    key=lambda field: field['pos'])
                else:
                    fields = cmd_data['fields']

                if 'fc_opts' in cmd_data:
                    fo = cmd_data['fc_opts']
                    # bs, stmin, wftmax
                    cmd_data['fc_opts'] = struct.pack("=BBB", fo[0], fo[1], fo[2])
                else:
                    cmd_data['fc_opts'] = None

                if 'pos' in fields[0] and not absolute_mode:
                    absolute_mode = True
                    cmd_data['autopad'] = True

                new_fields = []
                for field in fields:
                    self._log.debug(field)
                    # Non power of two types are hard as is. For now those can
                    # not be used in patterned fields.
                    if field.get('cnt', 1) > 1 and not is_power_of_two(field['width']):
                        raise ValueError('Non power of two field in patterned field not allowed')

                    if not field.get('width', 0) in FormatMap.keys():
                        raise ValueError('Unsupported field length')

                    if field.get('padding', 0) > 0:
                        if absolute_mode:
                            raise ValueError('padding not supported when using absolute mode')
                        field_fmt = str(field.get('padding')) + 'x'
                        self._log.debug("field_fmt(%s)", field_fmt)
                        fmt += field_fmt
                    elif not field.get('computed', False):
                        if absolute_mode:
                            pad = field['pos'] - fmt_last_pos - 1
                            if pad > 0:
                                if pad > 1:
                                    fmt += str(pad)
                                fmt += 'x'
                            elif pad < 0:
                                raise ValueError('negative padding encountered!!')

                            fmt_last_pos = field['pos'] + field.get('cnt', 1) * field['width'] - 1

                        # For patterned fields (i.e. cellVolts%02d) use multiplyer
                        # in format string.
                        field_fmt = str(field.get('cnt', ''))
                        if field.get('signed', False):
                            field_fmt += FormatMap[field['width']]['f'].lower()
                        else:
                            field_fmt += FormatMap[field['width']]['f'].upper()

                        self._log.debug(f"fmt({fmt} {field_fmt})")
                        fmt += field_fmt

                        if not is_power_of_two(field['width']):
                            if 'lambda' in field:
                                self._log.warning('defining lambda on non power ow two length fields may give unexpected results!')
                            else:
                                field['lambda'] = FormatMap[field['width']]['l']

                        field['scale'] = field.get('scale', 1)
                        field['offset'] = field.get('offset', 0)

                        if 'name' not in field:
                            raise ValueError('Name missing in Field')

                        start = field.get('idx', 0)
                        cnt = field.get('cnt', 1)

                        for field_idx in range(start, start + cnt):
                            # Expand patterned fields into simple fields to
                            # match the format string. Append new field to the
                            # array of new fields. We need to copy the existing
                            # field, else all field names will reference the same
                            # string
                            new_field = field.copy()
                            if cnt > 1:
                                new_field['name'] %= field_idx

                            new_field['fmt_idx'] = fmt_idx
                            new_field['fmt_len'] = len(FormatMap[field['width']])
                            fmt_idx += new_field['fmt_len']

                            new_fields.append(new_field)

                self._log.debug("fmt(%s)", fmt)
                cmd_data['autopad'] = cmd_data.get('autopad', False)
                cmd_data['struct'] = struct.Struct(fmt)
                cmd_data['fields'] = new_fields

    async def get_data(self, can_tries=1):
        """ Takes a structure which describes adresses,
            commands and how to decode the return """
        data = {}
        for cmd_data in self._fields:
            try:
                if cmd_data['computed']:
                    # Fields of computed "commands" are filled by executing
                    # the fields lambda with the data dict as argument
                    for field in cmd_data['fields']:
                        name = field['name']
                        func = field['lambda']
                        data[name] = func(data)
                else:
                    # Send a command to the CAN bus and parse the resulting
                    # bytearray using unpack. The format for unpack was generated
                    # in the preprocessor. Extracted values are scaled, shifted
                    # and a lambda function is executed if provided
                    can_try = 0
                    while True:
                        can_try += 1
                        try:
                            raw = await self._dongle.send_command_ex(cmd_data['cmd'],
                                                                     canrx=cmd_data['canrx'],
                                                                     cantx=cmd_data['cantx'],
                                                                     fc_opts=cmd_data['fc_opts'])
                            break
                        except NoData:
                            if can_try > can_tries:
                                raise
                    # Learn how much to pad a block on first encounter if autopadding is active
                    if cmd_data['autopad']:
                        pad = len(raw) - cmd_data['struct'].size
                        if pad > 0:
                            fmt = cmd_data['struct'].format
                            fmt += str(pad) + 'x'
                            cmd_data['struct'] = struct.Struct(fmt)
                            self._log.info("canid(0x%x) cmd(%s) len(%i) pad(%i)",
                                           cmd_data['cantx'], cmd_data['cmd'].hex(),
                                           len(raw), pad)
                        cmd_data['autopad'] = False

                    elif cmd_data['simple']:
                        width = len(raw) - cmd_data['struct'].size
                        assert 0 < width <= 8
                        fmt = cmd_data['struct'].format
                        if cmd_data['fields'][0].get('signed', False):
                            fmt += FormatMap[width]['f'].lower()
                        else:
                            fmt += FormatMap[width]['f'].upper()
                        cmd_data['struct'] = struct.Struct(fmt)
                        cmd_data['simple'] = False

                    raw_fields = cmd_data['struct'].unpack(raw)

                    for field in cmd_data['fields']:
                        name = field['name']
                        fmt_idx = field['fmt_idx']
                        fmt_len = field['fmt_len']

                        if 'lambda' in field:
                            value = field['lambda'](raw_fields[fmt_idx:fmt_idx+fmt_len])
                        else:
                            value = raw_fields[fmt_idx]

                        data[name] = value * field['scale'] + field['offset']

            except NoData:
                if not cmd_data.get('optional', False):
                    raise
            except struct.error as err:
                self._log.error("err(%s) cmd(%s) fmt(%s):%d raw(%s):%d", err, cmd_data['cmd'].hex(),
                                cmd_data['struct'].format, cmd_data['struct'].size,
                                raw.hex(), len(raw))
                raise

        return data
