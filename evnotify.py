""" Transmit data to EVNotify and handle notifications """
from asyncio import create_task
from time import monotonic
import logging
import EVNotifyAPI

EVN_SETTINGS_INTERVAL = 300
ABORT_NOTIFICATION_INTERVAL = 60

EXTENDED_FIELDS = {         # value is decimal places
    'auxBatteryVoltage': 1,
    'batteryInletTemperature': 1,
    'batteryMaxTemperature': 1,
    'batteryMinTemperature': 1,
    'cumulativeEnergyCharged': 1,
    'cumulativeEnergyDischarged': 1,
    'charging': 0,
    'normalChargePort': 0,
    'rapidChargePort': 0,
    'dcBatteryCurrent': 2,
    'dcBatteryPower': 2,
    'dcBatteryVoltage': 2,
    'externalTemperature': 1,
    'odo': 0,
    'soh': 0
}

ARMED = 0
SENT = 1
PENDING = -1


class EVNotify:
    """ Interface to EVNotify. """

    def __init__(self, config, car):
        self._log = logging.getLogger("EVNotiPi/EVNotify")
        self._log.info("Initializing EVNotify")

        self._car = car
        self._config = config
        self._poll_interval = config['interval']
        self._running = False

        self._data = []
        self._gps_data = []

        self._next_transmit = 0
        self._task = None

    def start(self):
        """ Start submit thread. """
        assert self._running is False
        self._running = True

        self._evn = EVNotifyAPI.EVNotify(self._config['akey'], self._config['token'])
        self._abort_notification = ARMED
        self._soc_notification = ARMED
        self._charging_start_soc = 0
        self._last_charging = monotonic()
        self._last_charging_soc = 0
        self._last_evn_settings_poll = 0
        self._is_charging = 0
        self._is_connected = 0
        self._settings = None
        self._soc_threshold = self._config.get('self._soc_threshold', 100)

        self._car.register_data(self.data_callback)

    def stop(self):
        """ Stop submit thread. """
        assert self._running is True
        self._car.unregister_data(self.data_callback)
        self._running = False

    async def data_callback(self, data):
        """ Callback to be called from 'car'. """
        self._log.debug("Enqeue...")
        self._data.append(data)

        if self._task is None or self._task.done():
            self._task = create_task(self.submit_data())

    async def submit_data(self):
        """ Thread that submits data to EVNotify in regular intervals. """
        log = self._log
        evn = self._evn

        now = monotonic()

        #log.info("Get self._settings from backend")
        #while self._running and self._settings is None:
        #    try:
        #        self._settings = evn.getSettings()
        #    except EVNotifyAPI.RateLimit as err:
        #        log.error("Rate Limited, sleeping 60s %s", err)
        #        sleep(60)
        #    except EVNotifyAPI.CommunicationError as err:
        #        log.info("Waiting for network connectivity (%s)", err)
        #        sleep(3)

        #while self._running:
        if now >= self._next_transmit and len(self._data_queue) > 0:

            log.debug("Transmit...")

            avgs = {
                'dcBatteryCurrent': [],
                'dcBatteryPower': [],
                'dcBatteryVoltage': [],
                'speed': [],
                'latitude': [],
                'longitude': [],
                'altitude': [],
            }

            for data in self._data:
                for key, values in avgs.items():
                    if data.get(key, None) is not None:
                        values.append(data[key])

            # Need to copy data here because we update it later
            data = self._data[-1]

            self._data.clear()

            # Detect aborted charge
            if ((now - self._last_charging > ABORT_NOTIFICATION_INTERVAL and
                 self._charging_start_soc > 0 and 0 < self._last_charging_soc < self._soc_threshold and
                 self._abort_notification is ARMED) or self._abort_notification is PENDING):
                log.info("Aborted charge detected, send abort notification now-self._last_charging(%i) self._charging_start_soc(%i) self._last_charging_soc(%i) self._soc_threshold(%i) self._abort_notification(%i)",
                         now - self._last_charging, self._charging_start_soc, self._last_charging_soc,
                         self._soc_threshold, self._abort_notification)
                try:
                    await evn.sendNotification(True)
                    self._abort_notification = SENT
                except EVNotifyAPI.RateLimit as err:
                    log.error("Rate Limited, sleeping 60s %s", err)
                    self._next_transmit = monotonic() + 60
                    return
                except EVNotifyAPI.CommunicationError as err:
                    log.error("Communication Error: %s", err)
                    self._abort_notification = PENDING

            data.update({k: sum(v)/len(v)
                         for k, v in avgs.items() if len(v) > 0})

            try:
                if (data['SOC_DISPLAY'] is not None or
                        data['SOC_BMS'] is not None):

                    current_soc = data['SOC_DISPLAY'] or data['SOC_BMS']
                    self._is_charging = bool(data['charging'])
                    self._is_connected = bool(data['normalChargePort'] or data['rapidChargePort'])

                    if self._is_charging:
                        self._last_charging = now
                        self._last_charging_soc = current_soc

                    await evn.setSOC(data['SOC_DISPLAY'], data['SOC_BMS'])
                    extended_data = {a: round(data[a], EXTENDED_FIELDS[a])
                                     for a in EXTENDED_FIELDS if data[a] is not None}
                    log.debug(extended_data)
                    await evn.setExtended(extended_data)

                if data['fix_mode'] > 1 and not self._is_charging and not self._is_connected:
                    location = {a: data[a]
                                for a in ('latitude', 'longitude', 'speed')}
                    await evn.setLocation({'location': location})

                # Notification handling from here on
                if self._is_charging and now - self._last_evn_settings_poll > EVN_SETTINGS_INTERVAL:
                    try:
                        self._settings = await evn.getSettings()
                        self._last_evn_settings_poll = now

                        if 'soc' in self._settings:
                            new_soc = int(self._settings['soc'])
                            if new_soc != self._soc_threshold:
                                self._soc_threshold = new_soc
                                log.info("New notification threshold: %i",
                                         self._soc_threshold)

                    except EVNotifyAPI.RateLimit as err:
                        log.error("Rate Limited, sleeping 60s %s", err)
                        self._next_transmit = monotonic() + 60
                        return
                    except EVNotifyAPI.CommunicationError as err:
                        log.error("Communication error occured %s", err)

                # track charging started
                if self._is_charging and self._charging_start_soc == 0:
                    self._charging_start_soc = current_soc or 0
                elif not self._is_connected:   # Rearm abort notification
                    self._charging_start_soc = 0
                    self._abort_notification = ARMED

                # SoC threshold notification
                if ((self._is_charging and 0 < self._last_charging_soc < self._soc_threshold <= current_soc)
                        or self._soc_notification is PENDING):
                    log.info("Notification threshold(%i) reached: %i",
                             self._soc_threshold, current_soc)
                    try:
                        await evn.sendNotification()
                        self._soc_notification = ARMED
                    except EVNotifyAPI.RateLimit as err:
                        log.error("Rate Limited, sleeping 60s %s", err)
                        self._next_transmit = monotonic() + 60
                        return
                    except EVNotifyAPI.CommunicationError as err:
                        log.info("Communication Error: %s", err)
                        self._soc_notification = PENDING

            except EVNotifyAPI.RateLimit as err:
                log.error("Rate Limited, sleeping 60s %s", err)
                self._next_transmit = monotonic() + 60
                return
            except EVNotifyAPI.CommunicationError as err:
                log.info("Communication Error: %s", err)

            # Prime next loop iteration
            self._next_transmit = now + self._poll_interval

    def check_thread(self):
        """ Return the status of the thread """
        return self._running
