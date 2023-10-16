""" Module implementing an interface through Linux's socket CAN interface """
from asyncio import sleep, open_connection
from socket import (socket, timeout as sock_timeout,
                    AF_CAN, SOCK_DGRAM, CAN_ISOTP, CAN_EFF_FLAG, CAN_EFF_MASK,
                    SOL_CAN_BASE)
from struct import Struct, pack
import logging
from pyroute2 import IPRoute
from . import NoData, CanError

SOL_CAN_ISOTP = SOL_CAN_BASE + CAN_ISOTP
CAN_ISOTP_OPTS = 1
CAN_ISOTP_RECV_FC = 2
CAN_ISOTP_TX_STMIN = 3
CAN_ISOTP_RX_STMIN = 4
CAN_ISOTP_LL_OPTS = 5
CAN_ISOTP_EXTEND_ADDR = 0x2
CAN_ISOTP_TX_PADDING = 0x4
CAN_ISOTP_RX_PADDING = 0x8
CAN_ISOTP_CHK_PAD_LEN = 0x10
CAN_ISOTP_CHK_PAD_DATA = 0x20

CANFMT = Struct("<IB3x8s")


def can_str(msg):
    """ Returns a text representation of a CAN frame """
    can_id, length, data = CANFMT.unpack(msg)
    return "%x#%s (%d)" % (can_id & CAN_EFF_MASK, data.hex(' '), length)


class IsoTpSocket():
    """ Extend socket class with some helper functions """

    async def __init__(self, can_port, canrx, cantx, fc_opts=None):
        self._socket = socket(AF_CAN, SOCK_DGRAM, CAN_ISOTP)
        self._canrx = canrx
        self._cantx = cantx
        self._can_port = can_port
        self._can_id = None
        self._can_mask = None
        self._can_filter = None

        opts = CAN_ISOTP_TX_PADDING | CAN_ISOTP_RX_PADDING | CAN_ISOTP_CHK_PAD_LEN
        sock_opt_isotp_opt = pack("=LLBBBB", opts, 0, 0, 0xAA, 0xFF, 0)
        sock_opt_isotp_fc = pack("=BBB", 0, 0, 0) if fc_opts is None else fc_opts

        self._socket.setsockopt(SOL_CAN_ISOTP, CAN_ISOTP_OPTS,
                                sock_opt_isotp_opt)
        self._socket.setsockopt(SOL_CAN_ISOTP, CAN_ISOTP_RECV_FC,
                                sock_opt_isotp_fc)

        self._socket.bind((can_port, canrx, cantx))
        self._socket.settimeout(0.2)

        self._reader, self._writer = await open_connection(self._socket)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        self._writer.close()
        await self._writer.wait_closed()

    async def send(self, data, timeout=None):
        """ async write to CAN """
        if timeout is not None:
            self._socket.settimeout(timeout)
        self._writer.write(data)
        await self._writer.drain()

    async def recv(self, length=-1, timeout=None):
        """ async read from CAN """
        if timeout is not None:
            self._socket.settimeout(timeout)
        return await self._reader.read(length)


class SocketCan:
    """ Socket CAN interface """

    def __init__(self, config):
        self._log = logging.getLogger("EVNotiPi/SocketCAN")
        self._log.info("Initializing SocketCAN")
        self._config = config
        self._is_extended = False
        self._loop = None

        self.init_dongle()

    def init_dongle(self):
        """ Set up the network interface and initialize socket """
        ip_route = IPRoute()
        ifidx = ip_route.link_lookup(ifname=self._config['port'])[0]
        link = ip_route.link('get', index=ifidx)
        if 'state' in link[0] and link[0]['state'] == 'up':
            ip_route.link('set', index=ifidx, state='down')
            sleep(1)

        ip_route.link('set', index=ifidx, type='can',
                      txqlen=4000, bitrate=self._config['speed'],
                      state='up')
        ip_route.close()

    async def send_command_ex(self, cmd, cantx, canrx, fc_opts=None):
        """ Send a command using specified can tx id and
            return response from can rx id.
            Implemented using kernel level iso-tp. """
        if self._log.isEnabledFor(logging.DEBUG):
            self._log.debug("sendCommandEx_ISOTP cmd(%s) cantx(%x) canrx(%x)",
                            cmd.hex(' '), cantx, canrx)

        if self._is_extended:
            cantx |= CAN_EFF_FLAG
            canrx |= CAN_EFF_FLAG

        try:
            async with IsoTpSocket(self._config['port'],
                                   canrx, cantx, fc_opts) as sock:
                if self._log.isEnabledFor(logging.DEBUG):
                    self._log.debug("canrx(%s) cantx(%s) cmd(%s)",
                                    hex(canrx), hex(cantx), cmd.hex(' '))
                await sock.send(cmd)
                data = await sock.recv(512)
                if self._log.isEnabledFor(logging.DEBUG):
                    self._log.debug(data.hex(' '))
        except sock_timeout as err:
            raise NoData(f'Command timed out {cmd.hex(" ")}: {err}') from err
        except OSError as err:
            raise CanError(f'Failed Command {cmd.hex(" ")}: {err}') from err

        if not data or len(data) == 0:
            raise NoData('NO DATA')

        return data

    def set_protocol(self, prot):
        """ select the CAN flavor """
        if prot == 'CAN_11_500':
            self._is_extended = False
        elif prot == 'CAN_29_500':
            self._is_extended = True
        else:
            raise ValueError(f'Unsupported protocol {prot}')

        self.init_dongle()
