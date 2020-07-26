#!/usr/bin/env python3

import logging
import cProfile
import pstats
import io
from pstats import SortKey
from pprint import PrettyPrinter
from sys import argv
import car
import dongle
import watchdog

logging.basicConfig(level=logging.DEBUG)

pp = PrettyPrinter(indent=2)
pp = pp.pprint

pr = cProfile.Profile()

DONGLE = dongle.load('FakeDongle')
WATCHDOG = watchdog.load('DUMMY')
CAR = car.load(argv[1])

watchdog = WATCHDOG({})
dongle = DONGLE({'car_type': argv[1]})
gps = None
car = CAR({'interval': 1}, dongle, watchdog, gps)

data = {}

if False:
#if True:
    pr.enable()
    for i in range(0, 100000):
        car.read_dongle(data)
    pr.disable()
    s = io.StringIO()
    sortby = SortKey.CUMULATIVE
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats()
    ps.print_callers()
    print(s.getvalue())
else:
    car.read_dongle(data)
    pp(data)
