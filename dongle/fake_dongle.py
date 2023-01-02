""" Dongle for testing """

B = bytes.fromhex

B2101 = bytes.fromhex('2101')
B2102 = bytes.fromhex('2102')
B2103 = bytes.fromhex('2103')
B2104 = bytes.fromhex('2104')
B2105 = bytes.fromhex('2105')
B2180 = bytes.fromhex('2180')
B220100 = bytes.fromhex('220100')
B220101 = bytes.fromhex('220101')
B220102 = bytes.fromhex('220102')
B220103 = bytes.fromhex('220103')
B220104 = bytes.fromhex('220104')
B220105 = bytes.fromhex('220105')
B220106 = bytes.fromhex('220106')
B220106010a = bytes.fromhex('220106010a')
B22010a = bytes.fromhex('22010a')
B22010b = bytes.fromhex('22010b')
B22010c = bytes.fromhex('22010c')
B22b002 = bytes.fromhex('22b002')
B22c00b = bytes.fromhex('22c00b')
B22e001 = bytes.fromhex('22e001')
B22e004 = bytes.fromhex('22e004')
B22e011 = bytes.fromhex('22e011')


data = {
    'IONIQ_BEV': {
        0x7e4: {
            B2101:   bytes.fromhex("""6101FFFFFFFF
                                    A5264326480300
                                    070EE912121212
                                    1212120012C615
                                    C60A0000910003
                                    4F0E00034C0400
                                    01374300012C20
                                    009B02DE0D017D
                                    0000000003E800""")[:0x03d],
            B2102:   bytes.fromhex("""6102FFFFFFFF
                                    C6C6C6C6C6C6C6
                                    C6C6C6C6C6C6C6
                                    C6C6C6C6C6C6C6
                                    C6C6C6C6C6C6C6
                                    C6C6C6C6000000""")[:0x026],
            B2103:   bytes.fromhex("""6103FFFFFFFF
                                    C6C6C6C6C6C6C6
                                    C6C6C6C6C6C6C6
                                    C6C6C6C6C6C6C6
                                    C6C6C6C6C6C6C6
                                    C6C6C6C6000000""")[:0x026],
            B2104:   bytes.fromhex("""6104FFFFFFFF
                                    C6C6C6C6C6C6C6
                                    C6C6C6C6C6C6C6
                                    C6C6C6C6C6C6C6
                                    C6C6C6C6C6C6C6
                                    C6C6C6C6000000""")[:0x026],
            B2105:   bytes.fromhex("""6105FFFFFFFF
                                    00000000001212
                                    12121212122643
                                    26480001501112
                                    03E81003E80AAD
                                    00310000000000
                                    00000000000000""")[:0x02d],
            },
        0x7e6: {
            B2180:   bytes.fromhex("""6180C366C000
                                    01130000000000
                                    2273003B3A0000
                                    7A130096960000""")[:0x019],
            },
        0x7c6: {
            B22b002: bytes.fromhex("""62B002E00000
                                    0000AD00B56C00
                                    00000000000000""")[:0x00f],
            }
        },
    'IONIQ_FL_EV': {
        0x7e4: {
            B220101: bytes.fromhex("""620101FFFDE7
                                    FFC10000000003
                                    00060E491F1E1E
                                    1D1D1F1F001BD0
                                    09CF2500009400
                                    05516200047810
                                    0001C924000168
                                    A0005D9CB00D01
                                    6D0000000003E8""")[:0x03e],
            B220102: bytes.fromhex("""620102FFFFFF
                                    FFCFCFCFCFCFCF
                                    CFCFD0CFCFD0CF
                                    CFCFCFCFCFCFCF
                                    CFCFCFCFCFCFCF
                                    CFCFCFCFCFAAAA""")[:0x027],
            B220103: bytes.fromhex("""620103FFFFFF
                                    FFCFCFCFCFCFCF
                                    CFCFCFCFCFCFCF
                                    CFCFCFCFCFCFCF
                                    CFCFCFCFCFCFCF
                                    CFCFCFCFCFAAAA""")[:0x027],
            B220104: bytes.fromhex("""620104FFFFFF
                                    00CFCFCFCFCFCF
                                    CFCFCFCFCFCFCF
                                    CFCFCFCFCFCFCF
                                    CFCFCFCF010000
                                    0000000402AAAA""")[:0x027],
            B220105: bytes.fromhex("""620105003F46
                                    10000000000000
                                    0000001B940010
                                    EC2C2400015019
                                    C703E80903E823
                                    C7001002090525
                                    186D010000AAAA""")[:0x02e],
            },
        0x7c6: {
            B22b002: bytes.fromhex("""62B002E00000
                                    00FFB300862900
                                    00000000000000""")[:0x00f],
            },
        },
    'EV6': {
        0x744: {
            B22e004: B('62 E0 04 FF FE 00 00 04 00 01 01 3E 3E 3D 45 45 46 20 00 00 00 05 D7'),
            },
        0x7a0: {
            B22c00b: B('62 c0 0b ff ff ff 80 b5 3f 00 04 00 b6 41 00 04 00 b5 40 00 04 00 b8 41 00 04 00 3d 99 b0 9b b0 9a b0 9b b0')},
        0x7b3: {
            B220100: B('62 01 00 7f d4 07 c8 ff 71 69 52 00 df 56 00 e4 56 ff 1c ff 96 ff ff ff ff ff ff ff 37 1b 75 73 00 ff ff 01')},
        0x7c6: {
            B22b002: B('62 b0 02 e0 00 00 00 ff b5 00 03 9a 00 00 00')},
        0x7e4: {
            B220101: B('62 01 01 ef fb e7 ef 9f 00 00 00 00 00 00 08 1d b6 10 0f 0f 10 0f 0f 0f 00 35 c6 26 c5 33 00 00 8d 00 00 0e e3 00 00 0d c9 00 00 0b 0e 00 00 09 d3 00 12 21 a4 00 02 f7 00 00 00 00 0b b8'),
            B220102: B('62 01 02 ff ff ff ff c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6'),
            B220103: B('62 01 03 ff ff ff ff c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c5 c6 c6 c5 c5 c6 c6 c6 c6 c6 c6 c6 c6 c6'),
            B220104: B('62 01 04 ff ff ff ff c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c5 c6 c6 c6 c6 c6'),
            B220105: B('62 01 05 FF FB 74 0F 01 2C 01 01 2C 0B 0A 0A 09 0A 0A 0B 58 D4 6A 0A 00 00 50 0A 00 03 E8 04 62 AB 00 8F 00 00 00 00 00 00 00 0A 0B 09 0A'),
            B220106: B('62 01 06 17 F8 11 00 0A 00 08 00 00 00 00 00 28 7B 00 00 00 00 00 00 07 00 EA 00 00 00 00 00 00 00 00 00 00 00 00'),
            B220106010a: B('62 01 06 17 F8 11 00 0A 00 08 00 00 00 00 00 27 7C 00 00 00 00 00 00 07 00 EA 00 00 00 00 00 00 00 00 00 00 00 00 01 0A'),
            B22010a: B('62 01 0a ff ff ff ff c6 c6 c6 c6 c6 c6 c6 c5 c6 c6 c6 c6 c5 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6'),
            B22010b: B('62 01 0b ff ff ff ff c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6'),
            B22010c: B('62 01 0c ff ff ff ff c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c6 c5'),
            },
        0x7e3: {
            B22e001: B('62 E0 01 FF FF FF FF 60 09 9F 91 D6 35 00 38 04 05 05 4B 37 00 00 00 00 00 00 1B 00 A5 05 11 05 FC FF FD FF FC FF CD AB 1F 09 05 25 05 93 0B EC 04 C2 CD 11 00 15 FA 04 00 54 F7 84 04 C1 CD EC 03 0F FA C1 CD ED 03 B9 FD 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00'),
            },
        0x7e5: {
            B22e011: B('62 E0 11 FF FF FF F8 01 01 00 00 00 70 38 30 04 1B 1D 0C 37 90 80 0B 61 20 6B 00 66 08 01 01 01 00 0A 00 00 12 00 07 00 00 00 00 00 00 00 00 00 00'),
            },
        }
    }

class FakeDongle:
    def __init__(self, config):
        self._data = data[config['car_type']]

    def send_command_ex(self, cmd, cantx, canrx):
        return self._data[cantx][cmd]

    def set_protocol(self, bla):
        pass
