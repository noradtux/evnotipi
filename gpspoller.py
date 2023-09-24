""" Interface to gpsd """
from asyncio import sleep, create_task
from time import strptime
from calendar import timegm
import json
import logging
import socket


def empty_fix():
    """ Return an empty fix so all fields are guaranteed to exist. """
    return {
        'device': None,
        'mode': 0,
        'latitude': None,
        'longitude': None,
        'speed': None,
        'altitude': None,
        'heading':  None,
        'time': None,
        'xdop': None,
        'ydop': None,
        'vdop': None,
        'tdop': None,
        'hdop': None,
        'gdop': None,
        'pdop': None,
    }


class GpsPoller:
    """ Thread that continously reads data from gpsd. """

    def __init__(self, config):
        """ store: json file to store last valid fix on shutdown """

        self._log = logging.getLogger("EVNotiPi/GPSPoller")
        self._task = None
        self._gpsd = ('localhost', 2947)
        self._last_fix = empty_fix()
        self._store = config.get('store')
        self._precission = config.get('precission', 10)
        self._running = False

    async def run(self):
        """ The reader thread. """
        self._running = True
        gps_sock = None
        precission = self._precission
        last_gdop = precission + 1  # Make sure, last_gdop <= precission is false
        while self._running:
            try:
                if gps_sock:
                    data = await gps_sock.recv(4096)
                    for line in data.split(b'\r\n'):
                        if len(line) == 0:
                            continue
                        try:
                            fix = json.loads(line)
                            if 'class' not in fix:
                                continue

                            if fix['class'] == 'TPV' and last_gdop <= precission:
                                fix_time = timegm(strptime(fix['time'],
                                                           "%Y-%m-%dT%H:%M:%S.%fZ"))

                                self._last_fix.update({
                                    'device':    fix['device'],
                                    'mode':      fix['mode'],
                                    'latitude':  fix.get('lat'),
                                    'longitude': fix.get('lon'),
                                    'speed':     fix.get('speed'),
                                    'altitude':  fix.get('altMSL'),
                                    'heading':   fix.get('track'),
                                    'time':      fix_time,
                                })
                                if (self._last_fix['speed'] is not None and
                                        0 < self._last_fix['speed'] < 1):
                                    self._last_fix['speed'] = 0
                            elif fix['class'] == 'SKY':
                                if 'gdop' in fix:
                                    last_gdop = fix['gdop']

                                self._last_fix.update({
                                    'xdop': fix.get('xdop', None),
                                    'ydop': fix.get('ydop', None),
                                    'vdop': fix.get('vdop', None),
                                    'tdop': fix.get('tdop', None),
                                    'hdop': fix.get('hdop', None),
                                    'gdop': fix.get('gdop', None),
                                    'pdop': fix.get('pdop', None),
                                })

                        except json.decoder.JSONDecodeError:
                            self._log.error("JSONDecodeError %s", line)
                else:
                    gps_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    gps_sock.connect(self._gpsd)
                    gps_sock.settimeout(1)
                    gps_sock.recv(1024)
                    gps_sock.sendall(b'?WATCH={"enable":true,"json":true};')
            except socket.timeout:
                sleep(0.1)
            except (StopIteration, ConnectionResetError, OSError) as err:
                self._log.info('Problem encountered. Resetting socket. (%s)', err)
                gps_sock.close()
                gps_sock = None
                self._last_fix = empty_fix()
                sleep(1)

    def fix(self):
        """ Return the last fix. """
        return self._last_fix

    def start(self):
        """ Start the poller thread. """
        if self._store:
            try:
                with open(self._store, encoding='utf-8') as store_file:
                    new_fix = json.load(store_file)
                self._last_fix['latitude'] = new_fix['latitude']
                self._last_fix['longitude'] = new_fix['longitude']
                self._last_fix['altitude'] = new_fix['altitude']
            except FileNotFoundError:
                self._log.warn('File not found (%s)', self._store)

        self._running = True
        self._task = create_task(self.run(), name='GpsPoller')

    def stop(self):
        """ Stop the poller thread. """
        self._running = False
        #self._task.join()
        if self._store:
            with open(self._store, 'w', encoding='utf-8') as store_file:
                json.dump(self._last_fix, store_file)

    def check_task(self):
        """ Return running state if the poller thread. """
        return self._task.is_alive()
