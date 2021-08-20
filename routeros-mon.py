#!/usr/bin/env python3

import yaml
from time import sleep, time
from datetime import datetime, timezone
import re
import pyrfc3339
import routeros_api
from influxdb_client import InfluxDBClient, WriteOptions

with open('config.yaml', encoding='utf-8') as config_file:
    C = None
    for config in yaml.load_all(config_file, Loader=yaml.SafeLoader):
        C = config

Influx = InfluxDBClient(url=C['influxdb']['url'],
                        org=C['influxdb']['org'],
                        token=C['influxdb']['token'],
                        enable_gzip=True)

opts = WriteOptions(batch_size=10000,
                    flush_interval=60000,
                    jitter_interval=5000)

write_api = Influx.write_api(write_options=opts)

connection = routeros_api.RouterOsApiPool('192.168.8.2',
                                          username='api-ro',
                                          password='api-ro',
                                          use_ssl=False,
                                          plaintext_login=True)
api = connection.get_api()

lte = api.get_resource('/interface/lte')
lte_id = lte.get()[0]['id']
gps = api.get_resource('/system/gps')

while True:
    #gps_data = gps.call('monitor', {'once': '1'})
    lte_data = lte.call('monitor', {'id': lte_id, 'once': '1'})[0]
    fields = {}
    for i in ('lac', 'current_cellid', 'enb-id', 'sector-id', 'phy-cellid'):
        if i in lte_data:
            fields[i] = int(lte_data[i])
              
    for i in ('rssi', 'rsrp', 'rsrq', 'sinr', 'cqi', 'ri'):
        if i in lte_data:
            fields[i] = float(lte_data[i])

    #if gps_data['valid'] == 'true':
    #    for i in ('latitude', 'longitude', 'altitude', 'speed'):
    #        fields[i] = float(re.sub('[^0-9\.]', '', gps_data[i]))

    write_api.write(bucket=C['influxdb']['bucket'],
                    org=C['influxdb']['org'],
                    record=[{
                        'measurement': 'mobile_net',
                        'tags': {'akey': C['evnotify']['akey'], 'car': C['car']['type']},
                        'fields': fields,
                        'time': pyrfc3339.generate(
                            datetime.fromtimestamp(time(), timezone.utc)),
                        }]
                    )

    sleep(5)
