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
            idx = 0
            for field in cdata['fields']:
                fmt += str(field.get('cnt', '')) + field['format']
                field['cnt'] = field.get('cnt', 1)
                field['scale'] = field.get('scale', 1)
                field['offset'] = field.get('offset', 0)
                if 'name' in field:
                    field['fmt_idx'] = idx
                    field['fmt_len'] = len(field['format'] * field['cnt'])
                    idx += field['fmt_len']

            self._log.debug("fmt(%s)", fmt)
            cdata['cmd_format'] = fmt

    def get_data(self):
        """ Takes a structure which describes adresses,
            commands and how to decode the return """
        data = {}
        try:
            for cmd, cdata in self._fields.items():
                raw = self._dongle.sendCommandEx(cmd, canrx=cdata['canrx'],
                                                 cantx=cdata['cantx'])
                raw_fields = struct.unpack(cdata['cmd_format'], raw)

                for field in cdata['fields']:
                    if 'name' in field:
                        name = field['name']
                        fmt_idx = field['fmt_idx']
                        fmt_len = field['fmt_len']
                        field_cnt = field['cnt']
                        if field_cnt > 1:
                            base_idx = field['idx']

                        for idx in range(0, field_cnt):
                            if field_cnt > 1:
                                iname = name.format(base_idx + idx)
                            else:
                                iname = name

                            if 'lambda' in field:
                                value = field['lambda'](raw_fields[fmt_idx+idx:fmt_idx+idx+fmt_len])
                            else:
                                value = raw_fields[fmt_idx + idx]

                            data[iname] = value * field['scale'] + field['offset']

        except NoData:
            if not cdata.get('optional', False):
                raise
        except struct.error as e:
            self._log.error("cmd(%s) fmt(%s):%d raw(%s):%d", cmd.hex(),
                            cdata['cmd_format'], struct.calcsize(cdata['cmd_format']),
                            raw.hex(), len(raw))
            raise

        return data
