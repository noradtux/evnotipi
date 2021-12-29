#!/bin/env python3

from time import time, strftime, localtime
from socket import (socket, timeout as sock_timeout,
                    PF_CAN, SOCK_RAW, CAN_RAW,
                    CAN_EFF_MASK)
from struct import Struct

CANFMT = Struct("<IB3x8s")

can = socket(PF_CAN, SOCK_RAW, CAN_RAW)
can.bind(('can0',))

filehandles = {}

while True:
    msg = can.recv(72)
    can_id, length, msg_data = CANFMT.unpack(msg)
    can_id &= CAN_EFF_MASK

    if len(msg_data) == 0:
            continue

    if can_id not in filehandles:
        filehandles[can_id] = open('can0_%03x.can' % can_id, 'a')
    
    tstr = strftime('%Y-%m-%d %H:%M:%S', localtime(time()))
    filehandles[can_id].write("%s %03x [%i] %s\n" % (
                              tstr, can_id, length, msg_data.hex(' ')))


for fh in filehandles.values():
    fh.close()
