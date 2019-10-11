from subprocess import check_call,check_output
import logging

class WiFiCtrl:
    def __init__(self):
        self.log = logging.getLogger("EVNotiPi/WiFi")
        self.log.info("Initializing WiFi")

        self.state = None
        self.enable()

    def enable(self):
        if self.state != True:
            self.log.info("Enable WiFi")
            check_call(['/bin/systemctl','start','hostapd'])
            self.state = True

    def disable(self):
        if self.state != False:
            self.log.info("Disable WiFi")
            if check_output(['/sbin/iw','dev','wlan0','station','dump','|','wc','-0'])  == b'':
                check_call(['/bin/systemctl','stop','hostapd'])
                self.state = False
            else:
                self.log.info("Clients connected, not disabling WiFi")

