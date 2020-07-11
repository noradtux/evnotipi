import os
from importlib import import_module

def Load(dongle_type):
    if not "%s.py" % (dongle_type) in os.listdir('dongle'):
        raise Exception('Unsupported dongle %s' % (dongle_type))

    return getattr(import_module("dongle." + dongle_type), dongle_type)
