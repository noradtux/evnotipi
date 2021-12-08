""" Module for Peugeot e208 """
from .psa import Psa


class E208(Psa):
    """ Class for E208 """

    def get_base_data(self):
        return {
                "CAPACITY": 50,
                "SLOW_SPEED": 3.6,
                "NORMAL_SPEED": 11.0,
                "FAST_SPEED": 99.0
                }

    def get_abrp_model(self):
        return 'peugeot:e208:20:%d' % self.get_base_data()['CAPACITY']
