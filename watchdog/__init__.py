import os
from importlib import import_module

def Load(watchdog_type):
    if not "{}.py".format(watchdog_type) in os.listdir('watchdog'):
        raise Exception('Unsupported watchdog {}'.format(watchdog_type))

    return getattr(import_module("watchdog." + watchdog_type), watchdog_type)
