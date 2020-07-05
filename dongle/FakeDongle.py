""" Dongle for testing """

B2101 = bytes.fromhex('2101')
B2102 = bytes.fromhex('2102')
B2103 = bytes.fromhex('2103')
B2104 = bytes.fromhex('2104')
B2105 = bytes.fromhex('2105')
B2180 = bytes.fromhex('2180')
B22b002 = bytes.fromhex('22b002')

data = {
    'IONIQ_BEV': {
        0x7e4: {
            B2101:   bytes.fromhex("""6101FFFFFFFF
                                21A5264326480300
                                22070EE912121212
                                231212120012C615
                                24C60A0000910003
                                254F0E00034C0400
                                2601374300012C20
                                27009B02DE0D017D
                                280000000003E800""")[:0x03d],
            B2102:   bytes.fromhex("""6102FFFFFFFF
                                21C6C6C6C6C6C6C6
                                22C6C6C6C6C6C6C6
                                23C6C6C6C6C6C6C6
                                24C6C6C6C6C6C6C6
                                25C6C6C6C6000000""")[:0x026],
            B2103:   bytes.fromhex("""6103FFFFFFFF
                                21C6C6C6C6C6C6C6
                                22C6C6C6C6C6C6C6
                                23C6C6C6C6C6C6C6
                                24C6C6C6C6C6C6C6
                                25C6C6C6C6000000""")[:0x026],
            B2104:   bytes.fromhex("""6104FFFFFFFF
                                21C6C6C6C6C6C6C6
                                22C6C6C6C6C6C6C6
                                23C6C6C6C6C6C6C6
                                24C6C6C6C6C6C6C6
                                25C6C6C6C6000000""")[:0x026],
            B2105:   bytes.fromhex("""6105FFFFFFFF
                                2100000000001212
                                2212121212122643
                                2326480001501112
                                2403E81003E80AAD
                                2500310000000000
                                2600000000000000""")[:0x02d],
            },
        0x7e6: {
            B2180:   bytes.fromhex("""6180C366C000
                                2101130000000000
                                222273003B3A0000
                                237A130096960000""")[:0x019],
            },
        0x7c6: {
            B22b002: bytes.fromhex("""62B002E00000
                                210000AD00B56C00
                                2200000000000000""")[:0x00f],
            }
        }
    }

class FakeDongle:
    def __init__(self, config):
        self._data = data[config['car_type']]

    def sendCommandEx(self, cmd, cantx, canrx):
        return self._data[cantx][cmd]

    def setProtocol(self, bla):
        pass
