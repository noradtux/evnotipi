from subprocess import check_call, check_output
import logging


class WiFiCtrl:
    def __init__(self):
        self.log = logging.getLogger("EVNotiPi/WiFi")
        self.log.info("Initializing WiFi")
        self.log_flag = True

        self.state = None
        self.enable()

    def enable(self):
        if self.state is not True:
            self.log.info("Enable WiFi")
            check_call(['/bin/systemctl', 'start', 'hostapd'])
            self.state = True
            self.log_flag = True

    def disable(self):
        if self.state is not False:
            if check_output(['/sbin/iw', 'dev', 'wlan0', 'station', 'dump',
                             '|', 'wc', '-0']) == b'':
                self.log.info("Disable WiFi")
                check_call(['/bin/systemctl', 'stop', 'hostapd'])
                self.state = False
            elif self.log_flag:
                self.log.info("Clients connected, not disabling WiFi")
                self.log_flag = False
