""" Generic decoder for ISO-TP based cars """
from struct import unpack

class IsoTpDecoder:
    """ Generic decoder for ISO-TP based cars """
    def __init__(self, dongle, fields):
        self._dongle = dongle
        self._fields = fields

        self.preprocess_fields()

    def preprocess_fields(self):
        """ Preprocess field structure, creating format strings for unpack etc.,"""
        for cdata in self._fields.values():
            fmt = ""
            idx = 0
            for field in cdata['fields']:
                fmt += field['format']
                if 'name' in field:
                    field['fmt_idx'] = idx
                    field['fmt_len'] = len(field['format'])
                    idx += field['fmt_len']

            cdata['cmd_format'] = fmt


    def base_decode(self):
        """ Takes a structure which describes adresses,
            commands and how to decode the return """
        data = {}
        for cmd, cdata in self._fields.items():
            raw = self._dongle.sendCommandEx(cmd, canrx=cdata['canrx'], cantx=cdata['cantx'])
            struct = unpack(cdata['cmd_format'], raw)

            for field in cdata['fields']:
                name = field['name']
                fmt_idx = field['fmt_idx']
                fmt_len = field['fmt_len']
                if 'lambda' in field:
                    value = field['lambda'](struct[fmt_idx:fmt_idx+fmt_len])
                else:
                    value = struct[fmt_idx]

                data[name] = value * field.get('scale', 1) + field.get('offset', 0)

        return data
