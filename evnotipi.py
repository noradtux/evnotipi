#!/usr/bin/env python3
""" EVNotiPi main module """

import asyncio
from subprocess import check_call, check_output
from argparse import ArgumentParser
from time import monotonic
import sys
import signal
import os
import logging
import sdnotify
from gpspoller import GpsPoller
import watchdog
import dongle
import car
import evnotify

Systemd = sdnotify.SystemdNotifier()


class ThreadFailure(Exception):
    """ Raised when a sub thread fails """


parser = ArgumentParser(description='EVNotiPi')
parser.add_argument('-d', '--debug', dest='debug',
                    action='store_true', default=False)
parser.add_argument('-c', '--config', dest='config',
                    action='store', default='config.yaml')
args = parser.parse_args()
del parser

# load config
config = None
if os.path.exists(args.config):
    if args.config[-5:] == '.json':
        import json
        with open(args.config, encoding='utf-8') as config_file:
            config = json.load(config_file)
    elif args.config[-5:] == '.yaml':
        import yaml
        with open(args.config, encoding='utf-8') as config_file:
            # use the last document in config.yaml as config
            for c in yaml.load_all(config_file, Loader=yaml.SafeLoader):
                config = c
    else:
        raise ValueError('Unknown config type')
else:
    raise ValueError('No config found')

assert config is not None


if args.debug:
    logging.basicConfig(level=logging.DEBUG)
elif 'loglevel' in config:
    logging.basicConfig(level=config['loglevel'])
else:
    logging.basicConfig(level=logging.INFO)
log = logging.getLogger("EVNotiPi")

del args

# emulate old config if watchdog section is missing
if 'watchdog' not in config or 'type' not in config['watchdog']:
    raise ValueError('Old watchdog config syntax detected. '
                     'Please adjust according to config.yaml.template.')

Tasks = set()

# Load OBD2 interface module
DONGLE = dongle.load(config['dongle']['type'])

# Load car module
CAR = car.load(config['car']['type'])

# Load watchdog module
WATCHDOG = watchdog.load(config['watchdog']['type'])

# Init watchdog
watchdog = WATCHDOG(config['watchdog'])

# Init dongle
dongle = DONGLE(config['dongle'])

# Init GPS interface
gps = GpsPoller(config['gps'])
Tasks.add(gps)

# Init car
car = CAR(config['car'], dongle, watchdog, gps)

# Init EVNotify
EVNotify = evnotify.EVNotify(config['evnotify'], car)

# Init ABRP
if 'abrp' in config and config['abrp'].get('enable') is True:
    import abrp
    ABRP = abrp.ABRP(config['abrp'], car)

# Init influx interface
if 'influxdb' in config and config['influxdb'].get('enable') is True:
    import influx_telemetry
    Influx = influx_telemetry.InfluxTelemetry(
        config['influxdb'], car, gps, EVNotify)

# Init WiFi control
if 'wifi' in config and config['wifi'].get('enable') is True:
    from wifi_ctrl import WiFiCtrl
    wifi = WiFiCtrl()
else:
    wifi = None

# Init web service
if 'webservice' in config and config['webservice'].get('enable') is True:
    import webservice
    WebService = webservice.WebService(config['webservice'], car)
    Tasks.add(WebService)

LOG_USER = 1


async def main():
    """ main loop """

    # Suppress duplicate logs
    log_flags = 0

    # Start polling loops
    for task in Tasks:
        task.start()

    main_running = True
    try:
        while main_running:
            now = monotonic()

            await car.poll_data()

            Systemd.notify('WATCHDOG=1')

            if 'system' in config and 'shutdown_delay' in config['system']:
                if (now - car.last_data > config['system']['shutdown_delay'] and
                        not car.is_available()):
                    usercnt = int(check_output(['who', '-q']).split(b'\n')[1].split(b'=')[1])
                    if usercnt == 0:
                        log.info('Not charging and car off => Shutdown')
                        check_call(['/bin/systemctl', 'poweroff'])
                        main_running = False
                    elif not log_flags & LOG_USER:
                        log.info('Not charging and car off; Not shutting down, users connected')
                        log_flags |= LOG_USER
                elif log_flags & LOG_USER:
                    log_flags &= ~LOG_USER

            if wifi and config['wifi'].get('shutdown_delay') is not None:
                if (now - car.last_data > config['wifi']['shutdown_delay'] and
                        not car.is_available()):
                    wifi.disable()
                else:
                    wifi.enable()

            if main_running:
                await car.wait_next_poll()

    except (KeyboardInterrupt, SystemExit):  # when you press ctrl+c
        main_running = False
    finally:
        Systemd.notify('STOPPING=1')
        log.info('Exiting ...')
        for t in Tasks:  # reverse Threads
            t.stop()
        log.info('Bye.')

def exit_gracefully(signum, frame):
    """ Signalhandler for SIGTERM """
    sys.exit(0)


if __name__ == "__main__":
    # Set up signal handling
    signal.signal(signal.SIGTERM, exit_gracefully)

    Systemd.notify('READY=1')

    asyncio.run(main())
