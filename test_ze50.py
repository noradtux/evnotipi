#!/usr/bin/env python3

import logging
from pprint import PrettyPrinter
from sys import argv, exit
import car
import dongle
import watchdog

logging.basicConfig(level=logging.DEBUG)

pp = PrettyPrinter(indent=2)
pp = pp.pprint

DONGLE = dongle.load('SocketCAN')
WATCHDOG = watchdog.load('I2C')
CAR = car.load('ZOE_ZE50')

watchdog = WATCHDOG({})
dongle = DONGLE({'port': 'can0', 'speed': 500000})
gps = None
car = CAR({'interval': 1}, dongle, watchdog, gps)

data = {}

car.read_dongle(data)
pp(data)

exit(0)

################## Bus Scan ###################

IN_POWER = 22

LBC_RX = 0x18daf1db
LBC_TX = 0x18dadbf1
EVC_RX = 0x18daf1da
EVC_TX = 0x18dadaf1
BCB_RX = 0x18daf1de
BCB_TX = 0x18dadef1

# Scan EVC

current_min = IN_POWER / data['dcBatteryVoltage'] * .8
current_max = IN_POWER / data['dcBatteryVoltage'] * 1.2

for i in range(0x222000, 0x223fff):
    cmd = bytes.fromhex("%x" % i)
    raw = dongle.send_command_ex(cmd, canrx=EVC_RX, cantx=EVC_TX)

    value = int.from_bytes(raw[6:], byteorder='big', signed=true)

    if current_min <= value <= current_max:
        print("cmd(%s) value(%d)" % (cmd.hex(), value))
