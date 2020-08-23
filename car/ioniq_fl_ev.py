""" Module for Hyundai Ioniq Electric 38kWh """
from .kona_ev import KonaEv


class IoniqFlEv(KonaEv):
    """ Class for Hyundai Ioniq Electric 38kWh """

    @staticmethod
    def get_base_data():
        return {
            "CAPACITY": 38,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50.0
        }

    @staticmethod
    def get_abrp_model():
        return 'hyundai:ioniq:19:38:other'

    @staticmethod
    def get_evn_model():
        return 'IONIQ_FL_EV'
