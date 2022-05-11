""" MOdule for Kia EV6 """
from .e_gmp import E_GMP


class Ev6(E_GMP):
    """ Class for Kia EV6 """

    def get_base_data(self):
        return {
                "CAPACITY": 77,
                "SLOW_SPEED": 3.6,
                "NORMAL_SPEED": 11.0,
                "FAST_SPEED": 220.0
                }

    def get_evn_model(self):
        return 'EV6'

    def get_abrp_model(self):
        return 'kia:ev6:22:%d' % self.get_base_data()['CAPACITY']
