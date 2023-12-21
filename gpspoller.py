""" Interface to gpsd """
from threading import Thread
from time import sleep, strptime
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
        self._thread = None
        self._gpsd = ('localhost', 2947)
        self._last_fix = empty_fix()
        self._store = config.get('store')
        self._precission = config.get('precission', 10)
        self._running = False

    def run(self):
        """ The reader thread. """
        self._running = True
        gps_sock = None
        precission = self._precission
        last_gdop = precission + 1  # Make sure, last_gdop <= precission is false
        while self._running:
            try:
                if gps_sock:
                    data = gps_sock.recv(4096)
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
                                    'latitude':  round(fix.get('lat'), 6),
                                    'longitude': round(fix.get('lon'), 6),
                                    'speed':     round(fix.get('speed'), 1),
                                    'altitude':  round(fix.get('altMSL'), 0),
                                    'heading':   round(fix.get('track'), 0),
                                    'time':      fix_time,
                                })
                                if (self._last_fix['speed'] is not None and
                                        0 < self._last_fix['speed'] < 1):
                                    self._last_fix['speed'] = 0
                            elif fix['class'] == 'SKY':
                                if 'gdop' in fix:
                                    last_gdop = round(fix['gdop'], 1)

                                for dop in ('xdop', 'ydop', 'vdop', 'tdop',
                                            'hdop', 'gdop', 'pdop', 'gdop'):
                                    self._last_fix[dop] = round(fix[dop], 1) if dop in fix else None

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
        self._thread = Thread(target=self.run, name="EVNotiPi/GPS")
        self._thread.start()

    def stop(self):
        """ Stop the poller thread. """
        self._running = False
        self._thread.join()
        if self._store:
            with open(self._store, 'w', encoding='utf-8') as store_file:
                json.dump(self._last_fix, store_file)

    def check_thread(self):
        """ Return running state if the poller thread. """
        return self._thread.is_alive()
