#!/usr/bin/env python3

import car
import dongle
import watchdog
from pprint import PrettyPrinter

pp = PrettyPrinter(indent=2)
pp = pp.pprint

DONGLE = dongle.Load('FakeDongle')
WATCHDOG = watchdog.Load('DUMMY')
CAR = car.Load('IONIQ_BEV')

watchdog = WATCHDOG({})
dongle = DONGLE({'car_type': 'IONIQ_BEV'})
gps = None
car = CAR({'interval': 1}, dongle, watchdog, gps)

data = {}
car.readDongle(data)

pp(data)
