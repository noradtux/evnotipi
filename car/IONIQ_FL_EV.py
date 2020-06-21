from .KONA_EV import *

class IONIQ_FL_EV(KONA_EV):
    def getBaseData(self):
        return {
            "CAPACITY": 38,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50.0
        }

    def getABRPModel(self):
        return 'hyundai:ioniq:19:38:other'

    def getEVNModel(self):
        return 'IONIQ_FL_EV'
