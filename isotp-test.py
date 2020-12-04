""" test PIDs """
from socket import (socket, timeout as sock_timeout,
                    AF_CAN, PF_CAN, SOCK_DGRAM, SOCK_RAW, CAN_ISOTP,
                    CAN_RAW, CAN_EFF_FLAG, CAN_EFF_MASK, CAN_RAW_FILTER,
                    SOL_CAN_BASE, SOL_CAN_RAW)
from struct import Struct, pack
from time import sleep
import logging
import sys
from pyroute2 import IPRoute

class CanError(Exception): pass
class NoData(Exception): pass


CANFMT = Struct("<IB3x8s")

LOG = logging.getLogger("CanDebug")

if sys.version_info[0:2] < (3, 8):
    raise NotImplementedError("ISO-TP-test requires at least python 3.8!")


def can_str(msg):
    """ Returns a text representation of a CAN frame """
    can_id, length, data = CANFMT.unpack(msg)
    return "%x#%s (%d)" % (can_id & CAN_EFF_MASK, data.hex(' '), length)


class CanSocket(socket):
    """ Extend socket class with some helper functions """

    def __init__(self, family=-1, sock_type=-1, proto=-1, fileno=None):
        socket.__init__(self, family, sock_type, proto, fileno)
        self._can_id = None
        self._can_mask = None
        self._can_filter = None

    def set_can_id(self, can_id):
        """ Set the con id for transmission """
        if not isinstance(can_id, int):
            raise ValueError

        self._can_id = can_id

    def set_can_rx_mask(self, mask):
        """ Set the can receive mask """
        if not isinstance(mask, int):
            raise ValueError

        self._can_mask = mask

        if self._can_filter is not None:
            self.set_filters_ex([{
                'id':   self._can_filter,
                'mask': self._can_mask,
            }])

    def set_can_rx_filter(self, addr):
        """ Set the can receive filter """
        if not isinstance(addr, int):
            raise ValueError

        self._can_filter = addr

        if self._can_mask is not None:
            self.set_filters_ex([{
                'id':   self._can_filter,
                'mask': self._can_mask,
            }])

    def set_filters_ex(self, filters):
        """ Set filters on the socket """
        bin_filter = bytearray()
        for flt in filters:
            bin_filter.extend(pack("=II", flt['id'], flt['mask']))

        self.setsockopt(SOL_CAN_RAW, CAN_RAW_FILTER, bin_filter)


def init_dongle(port, speed):
    """ Set up the network interface and initialize socket """
    ip_route = IPRoute()
    ifidx = ip_route.link_lookup(ifname=port)[0]
    link = ip_route.link('get', index=ifidx)
    if 'state' in link[0] and link[0]['state'] == 'up':
        ip_route.link('set', index=ifidx, state='down')
        sleep(1)

    ip_route.link('set', index=ifidx, type='can',
                  txqlen=4000, bitrate=speed)
    ip_route.link('set', index=ifidx, state='up')
    ip_route.close()


def send_command_ex(port, cmd, cantx, canrx, canrx_mask=None, is_extended=False):
    """ Send a command using specified can tx id and
        return response from can rx id. """

    if canrx_mask is None:
        canrx_mask = 0x1fffffff if is_extended else 0x7ff

    LOG.debug("sendCommandEx_CANRAW cmd(%s) cantx(%x) canrx(%x & %x)",
              cmd.hex(' '), cantx, canrx, canrx_mask)

    if is_extended:
        cantx |= CAN_EFF_FLAG
        canrx |= CAN_EFF_FLAG

    try:
        cmd_len = len(cmd)
        assert cmd_len < 8

        msg_data = (bytes([cmd_len]) + cmd).ljust(8, b'\x00')  # Pad cmd to 8 bytes

        cmd_msg = CANFMT.pack(cantx, len(msg_data), msg_data)

        LOG.debug("%s send messsage", can_str(cmd_msg))

        with CanSocket(PF_CAN, SOCK_RAW, CAN_RAW) as sock:
            sock.bind((port,))
            sock.settimeout(0.2)

            sock.set_filters_ex([{
                'id':   canrx,
                'mask': canrx_mask
                }])

            sock.send(cmd_msg)

            data = None
            data_len = 0
            last_idx = 0

            while True:
                LOG.debug("waiting recv msg")
                msg = sock.recv(72)
                can_id, length, msg_data = CANFMT.unpack(msg)

                LOG.debug("Got %x %i %s", can_id,
                          length, msg_data.hex(' '))

                can_id &= CAN_EFF_MASK
                msg_data = msg_data[:length]
                frame_type = msg_data[0] & 0xf0

                if frame_type == 0x00:
                    LOG.debug("%s single frame", can_str(msg))

                    data_len = msg_data[0] & 0x0f
                    data = bytes(msg_data[1:data_len+1])

                elif frame_type == 0x10:
                    LOG.debug("%s first frame", can_str(msg))

                    data_len = (msg_data[0] & 0x0f) + msg_data[1]
                    data = bytearray(msg_data[2:])

                    LOG.debug("Send flow control message")

                    flow_msg = CANFMT.pack(cantx, 8, b'\x30\x00\x00\x00\x00\x00\x00\x00')

                    sock.send(flow_msg)

                    last_idx = 0

                elif frame_type == 0x20:
                    LOG.debug("%s consecutive frame", can_str(msg))

                    idx = msg_data[0] & 0x0f
                    if (last_idx + 1) % 0x10 != idx:
                        raise CanError("Bad frame order: last_idx(%d) idx(%d)" %
                                       (last_idx, idx))

                    frame_len = min(7, data_len - len(data))
                    data.extend(msg_data[1:frame_len+1])
                    last_idx = idx

                    if data_len == len(data):
                        # All frames seen, exit loop
                        break

                elif frame_type == 0x30:
                    raise CanError("Unexpected flow control: %s" % (can_str(msg)))
                else:
                    raise CanError("Unexpected message: %s" % (can_str(msg)))

    except sock_timeout as err:
        raise NoData("Command timed out %s: %s" % (cmd.hex(' '), err))
    except OSError as err:
        raise CanError("Failed Command %s: %s" % (cmd.hex(' '), err))

    if not data or data_len == 0:
        raise NoData('NO DATA')
    if data_len != len(data):
        raise CanError("Data length mismatch %s: %d vs %d %s" %
                       (cmd.hex(' '), data_len, len(data), data.hex(' ')))

    return data


def read_raw_frame(sock, timeout=None):
    """ Read a single frame. """
    try:
        sock.settimeout(timeout)

        msg = sock.recv(72)

        can_id, length, msg_data = CANFMT.unpack(msg)
        can_id &= CAN_EFF_MASK

        if len(msg_data) == 0:
            raise NoData(b'NO DATA')

        data = {
            'can_id': can_id,
            'data_len': length,
            'data': msg_data[:length]
            }

        return data

    except sock_timeout as err:
        raise CanError("Recv timed out: %s" % (err))
    except OSError as err:
        raise CanError("CAN read error: %s" % (err))


if __name__ == "__main__":
    init_dongle('can0', 500000)

