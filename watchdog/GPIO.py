import logging
import RPi.GPIO as GPIO

class GPIO:
    def __init__(self, config):
        self._log = logging.getLogger("EVNotiPi/GPIO-Watchdog")
        self._shutdown_pin = config.get('shutdown_pin', 24)
        self._pup_down = config.get('pup_down', 21)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._shutdown_pin, GPIO.IN, pull_up_down=self._pup_down)

    def getShutdownFlag(self):
        return GPIO.input(self._shutdown_pin) is False

    def getVoltage(self):
        return None

    def calibrateVoltage(self, realVoltage):
        pass
