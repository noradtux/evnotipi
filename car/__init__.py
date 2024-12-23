""" Helper functions for car modules """
from importlib import import_module

Modules = {
    'EV6': {'f': 'ev6', 'c': 'Ev6'},
    'IONIQ5': {'f': 'ioniq5', 'c': 'Ioniq5'},
    'IONIQ_BEV': {'f': 'ioniq_bev', 'c': 'IoniqBev'},
    'IONIQ_FL_EV': {'f': 'ioniq_fl_ev', 'c': 'IoniqFlEv'},
    'KONA_EV': {'f': 'kona_ev', 'c': 'KonaEv'},
    'NIRO_EV': {'f': 'niro_ev', 'c': 'NiroEv'},
    'ZOE_Q210': {'f': 'zoe_q210', 'c': 'ZoeQ210'},
    'ZOE_ZE50': {'f': 'zoe_ze50', 'c': 'ZoeZe50'},
    'E208': {'f': 'e208', 'c': 'E208'},
}


def load(car_type):
    """ Import a specific car module """
    if car_type not in Modules.keys():
        raise ValueError('Unsupported car %s' % (car_type))

    return getattr(import_module("car." + Modules[car_type]['f']),
                   Modules[car_type]['c'])
