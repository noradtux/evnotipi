#!/usr/bin/env python3

import os
import requests
import re
from serial import Serial
import time
import datetime
import pyrfc3339
import influxdb

# load config
if os.path.exists('config.json'):
    import json
    with open('config.json', encoding='utf-8') as config_file:
        C = json.loads(config_file.read())
elif os.path.exists('config.yaml'):
    import yaml
    with open('config.yaml', encoding='utf-8') as config_file:
        C = None
        for c in yaml.load_all(config_file, Loader=yaml.SafeLoader):
            C = c
else:
    raise Exception('No config found')

Influx = influxdb.InfluxDBClient(C['influxdb']['host'], C['influxdb']['port'],
        C['influxdb']['user'], C['influxdb']['pass'], C['influxdb']['dbname'],
        retries=1, timeout=5, ssl=C['influxdb']['ssl'] if 'ssl' in C['influxdb'] else False, verify_ssl=True)

##############################################################################

if __name__ == "__main__":
    ser = Serial("/dev/ttyUSB0")
    data_queue = []
    last_transmit = 0
    while True:
        line = ser.readline()
        if line[:6] == b'^RSSI:':
            now = time.time()
            data = {
                    'Strength': int(line[6:])
                    }
            now = time.time()
            data_queue.append({
                'measurement': 'mobile_net',
                'fields': data,
                'time': pyrfc3339.generate(datetime.datetime.fromtimestamp(now, datetime.timezone.utc)),
                'tags': {},
                })
            if now - last_transmit > 10:
                last_transmit = now
                try:
                    Influx.write_points(data_queue)
                    data_queue.clear()
                except Exception as e:
                    print("Exception", e)

#########################
