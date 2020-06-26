#!/usr/bin/env python3

import os
import requests
import re
import time
import datetime
import pyrfc3339
import influxdb
import lxml.html

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
        retries=1, timeout=5, ssl=C['influxdb']['ssl'] if 'ssl' in C['influxdb'] else False, verify_ssl=True, gzip=True)

##############################################################################

if __name__ == "__main__":
    data_queue = []
    conn = requests.Session()
    rex = re.compile(".*?([0-9,\.]+)\s+GB.*?")
    while True:
        now = time.time()
        try:
            resp = conn.get("https://pass.telekom.de/home?continue=true")
            html = lxml.html.fromstring(resp.text.encode('utf-8'))
            elem = html.xpath('//div[@class="passStatus"]//span[@class="colored"]')[0]

            used  = float(rex.match(elem.text_content())[1].replace(',','.'))
            limit = float(rex.match(elem.tail)[1].replace(',','.'))

            data = {
                    'volumeUsed': used,
                    'volumeLimit': limit
                    }
            data_queue.append({
                'measurement': 'mobile_net',
                'fields': data,
                'time': pyrfc3339.generate(datetime.datetime.fromtimestamp(now, datetime.timezone.utc)),
                'tags': {},
                })

            Influx.write_points(data_queue)
            data_queue.clear()
        except Exception as e:
            print("Exception", e)

        time.sleep(60)

#########################
