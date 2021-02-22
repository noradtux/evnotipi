#!/usr/bin/env python3

import os
import requests
import re
from serial import Serial
import time
import datetime
import pyrfc3339
from influxdb_client import InfluxDBClient, WriteOptions

net_re = re.compile(r"wwan0:" +
                    r"\s+(?P<bytes_rx>\d+)" +
                    r"\s+(?P<packets_rx>\d+)" +
                    r"\s+(?P<errs_rx>\d+)" +
                    r"\s+(?P<drop_rx>\d+)" +
                    r"\s+(?P<fifo_rx>\d+)" +
                    r"\s+(?P<frame_rx>\d+)" +
                    r"\s+(?P<compressed_rx>\d+)" +
                    r"\s+(?P<multicast_rx>\d+)" +
                    r"\s+(?P<bytes_tx>\d+)" +
                    r"\s+(?P<packets_tx>\d+)" +
                    r"\s+(?P<errs_tx>\d+)" +
                    r"\s+(?P<drop_tx>\d+)" +
                    r"\s+(?P<fifo_tx>\d+)" +
                    r"\s+(?P<colls_tx>\d+)" +
                    r"\s+(?P<carrier_tx>\d+)" +
                    r"\s+(?P<compressed_tx>\d+)")

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

Influx = InfluxDBClient(url=C['influxdb']['url'],
                        org=C['influxdb']['org'],
                        token=C['influxdb']['token'],
                        enable_gzip=True)

opts = WriteOptions(batch_size=10000,
                    flush_interval=60000,
                    jitter_interval=5000)
write_api = Influx.write_api(write_options=opts)

##############################################################################

if __name__ == "__main__":
    ser = Serial("/dev/ttyUSB0")
    while True:
        line = ser.readline()
        if line[:6] == b'^RSSI:':
            now = time.time()

            data = {
                'Strength': int(line[6:]),
                }

            with open('/proc/net/dev', 'r') as netdev:
                for line in netdev:
                    m = net_re.search(line)
                    if m is not None:
                        for key in ['bytes_rx', 'packets_rx', 'errs_rx', 'drop_rx',
                                    'fifo_rx', 'frame_rx', 'multicast_rx',
                                    'bytes_tx', 'packets_tx', 'errs_tx', 'drop_tx',
                                    'fifo_tx', 'colls_tx', 'carrier_tx']:
                            data[key] = int(m[key])

                        break

            write_api.write(bucket=C['influxdb']['bucket'],
                            org=C['influxdb']['org'],
                            record=[{
                                'measurement': 'mobile_net',
                                'tags': {'akey': C['evnotify']['akey'], 'car': C['car']['type']},
                                'fields': data,
                                'time': pyrfc3339.generate(
                                    datetime.datetime.fromtimestamp(now, datetime.timezone.utc)),
                                }])

#########################
