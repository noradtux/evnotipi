""" Module for Citroën ë-SpaceTourer """
from .psa import Psa


class ESpaceTourer(Psa):
    """ Class for ë-SpaceTourer """

    def get_base_data(self):
        return {
                "CAPACITY": 75,
                "SLOW_SPEED": 3.6,
                "NORMAL_SPEED": 11.0,
                "FAST_SPEED": 100.0
                }

    def get_abrp_model(self):
        return 'peugeot:etraveler:21:%d:citroen' % self.get_base_data()['CAPACITY']
