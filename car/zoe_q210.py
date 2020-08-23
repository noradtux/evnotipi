""" Module for the Zoe Q210 """
from .zoe import Zoe


class ZoeQ210(Zoe):
    """ Class for the Zoe Q210 """

    @staticmethod
    def get_base_data():
        return {
            "CAPACITY": 22,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 22.0,
            "FAST_SPEED": 43.0
        }

    @staticmethod
    def get_abrp_model():
        return 'renault:zoe:q210:22:other'

    @staticmethod
    def get_evn_model():
        return 'ZOE_Q210'
