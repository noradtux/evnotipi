import os
from importlib import import_module

def Load(car_type):
    if not "%s.py" % (car_type) in os.listdir('car'):
        raise Exception('Unsupported car %s' % (car_type))

    return getattr(import_module("car." + car_type), car_type)
