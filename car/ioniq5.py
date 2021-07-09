""" MOdule for Hyundai Ioniq 5 """
from .e_gmp import E_GMP


class Ioniq5(E_GMP):
    """ Class for Hyundai Ioniq 5 """

    def get_base_data(self):
        return {
                "CAPACITY": 74,
                "SLOW_SPEED": 3.6,
                "NORMAL_SPEED": 11.0,
                "FAST_SPEED": 220.0
                }

    def get_abrp_model(self):
        return 'hyundai:ioniq5:22:%d' % self.get_base_data()['CAPACITY']
