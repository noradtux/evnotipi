""" Generic decoder for ISO-TP based cars """
import logging
from struct import unpack, calcsize
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
                if 'name' in field:
                    field['fmt_idx'] = idx
                    field['fmt_len'] = len(field['format'] * field.get('cnt', 1))
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
                self._log.debug("fmt(%s) %i %i raw(%s)", cdata['cmd_format'],
                                calcsize(cdata['cmd_format']), len(raw), raw.hex())
                struct = unpack(cdata['cmd_format'], raw)

                for field in cdata['fields']:
                    if 'name' in field:
                        name = field['name']
                        fmt_idx = field['fmt_idx']
                        fmt_len = field['fmt_len']
                        field_cnt = field.get('cnt', 1)
                        base_idx = field.get('idx', 0)

                        for idx in range(0, field_cnt):
                            iname = name.format(base_idx + idx)
                            if 'lambda' in field:
                                value = field['lambda'](struct[fmt_idx+idx:fmt_idx+idx+fmt_len])
                            else:
                                value = struct[fmt_idx + idx]

                            data[iname] = value * field.get('scale', 1) + field.get('offset', 0)

        except NoData:
            if not cdata.get('optional', False):
                raise

        return data
