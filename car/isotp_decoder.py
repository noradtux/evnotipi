""" Generic decoder for ISO-TP based cars """
import logging
import struct
from dongle.dongle import NoData

class IsoTpDecoder:
    """ Generic decoder for ISO-TP based cars """
    def __init__(self, dongle, fields):
        self._log = logging.getLogger("EVNotiPi/ISO-TP-Decoder")
        self._dongle = dongle
        self._fields = fields

        self.preprocess_fields()

    def preprocess_fields(self):
        """ Preprocess field structure, creating format strings for unpack etc.,"""
        for cdata in self._fields.values():
            fmt = ">"
            fmt_idx = 0

            cdata['computed'] = cdata.get('computed', False)

            if cdata['computed'] == False:
                new_fields = []
                for field in cdata['fields']:
                    fmt += str(field.get('cnt', '')) + field['format']
                    field['scale'] = field.get('scale', 1)
                    field['offset'] = field.get('offset', 0)

                    if 'name' in field:
                        start = field.get('idx', 0)
                        cnt = field.get('cnt', 1)

                        for field_idx in range(start, start + cnt):
                            new_field = field.copy()
                            if cnt > 1:
                                new_field['name'] %= field_idx

                            new_field['fmt_idx'] = fmt_idx
                            new_field['fmt_len'] = len(field['format'])
                            fmt_idx += new_field['fmt_len']


                            new_fields.append(new_field)

                self._log.debug("fmt(%s)", fmt)
                cdata['cmd_format'] = fmt
                cdata['fields'] = new_fields

    def get_data(self):
        """ Takes a structure which describes adresses,
            commands and how to decode the return """
        data = {}
        try:
            for cmd, cdata in self._fields.items():
                if cdata['computed']:
                    for field in cdata['fields']:
                        name = field['name']
                        func = field['lambda']
                        data[name] = func(data)
                else:
                    raw = self._dongle.sendCommandEx(cmd, canrx=cdata['canrx'],
                                                     cantx=cdata['cantx'])
                    raw_fields = struct.unpack(cdata['cmd_format'], raw)

                    for field in cdata['fields']:
                        name = field['name']
                        fmt_idx = field['fmt_idx']
                        fmt_len = field['fmt_len']

                        if 'lambda' in field:
                            value = field['lambda'](raw_fields[fmt_idx:fmt_idx+fmt_len])
                        else:
                            value = raw_fields[fmt_idx]

                        data[name] = value * field['scale'] + field['offset']

        except NoData:
            if not cdata.get('optional', False):
                raise
        except struct.error as e:
            self._log.error("cmd(%s) fmt(%s):%d raw(%s):%d", cmd.hex(),
                            cdata['cmd_format'], struct.calcsize(cdata['cmd_format']),
                            raw.hex(), len(raw))
            raise

        return data
