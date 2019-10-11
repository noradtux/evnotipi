#!/usr/bin/env python3

import os
import requests
import re
import hashlib
import base64
import xml.etree.ElementTree as ET
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
        C = yaml.load(config_file, Loader=yaml.SafeLoader)
else:
    raise Exception('No config found')

Influx = influxdb.InfluxDBClient(C['influxdb']['host'], C['influxdb']['port'],
        C['influxdb']['user'], C['influxdb']['pass'], C['influxdb']['dbname'],
        retries = 1, timeout = 1)

##############################################################################

def login(baseurl, username, password):
    s = requests.Session()
    r = s.get(baseurl + "/html/index.html")
    csrf_tokens = grep_csrf(r.text)

    s.headers.update({
    '__RequestVerificationToken': csrf_tokens[0]
    })

    # test token on statistics api
    # r = s.get(baseurl + "/api/monitoring/statistic-server")

    data = login_data(username, password, csrf_tokens[0])
    r = s.post(baseurl + "/api/user/login", data=data)

    s.headers.update({
    '__RequestVerificationToken': r.headers["__RequestVerificationToken"]
    })

    return s


def reboot(baseurl, session):
    s.post(baseurl + "/api/device/control", data='1')


def getData(baseurl, session):
    r = s.get(baseurl + "/api/monitoring/status")
    xml = ET.fromstring(r.text)
    SignalStrength = xml.findall("./SignalIcon")[0].text
    r = s.get(baseurl + "/api/monitoring/traffic-statistics")
    xml = ET.fromstring(r.text)
    TotalUpload = xml.findall("./TotalUpload")[0].text
    TotalDownload = xml.findall("./TotalDownload")[0].text

    return {
            'Strength': int(SignalStrength),
            'Upload': int(TotalUpload),
            'Download': int(TotalDownload)
            }


def grep_csrf(html):
    pat = re.compile(r".*meta name=\"csrf_token\" content=\"(.*)\"", re.I)
    matches = (pat.match(line) for line in html.splitlines())
    return [m.group(1) for m in matches if m]


def login_data(username, password, csrf_token):
    def encrypt(text):
        m = hashlib.sha256()
        m.update(bytes(text, 'utf-8'))
        return str(base64.b64encode(bytes(m.hexdigest(),'utf-8')))

    password_hash = encrypt(username + encrypt(password) + csrf_token)

    return '%s%s4' % (username, password_hash)


WEB = C['huawei']['url']
USERNAME = C['huawei']['user']
PASSWORD = C['huawei']['pass']

if __name__ == "__main__":
    s = login(WEB, USERNAME, PASSWORD)
    now = 0
    data_queue = []
    while True:
        now = time.time()
        data = getData(WEB, s)
        data_queue.append({
            'measurement': 'mobile_net',
            'fields': data,
            'time': pyrfc3339.generate(datetime.datetime.fromtimestamp(now, datetime.timezone.utc)),
            'tags': {},
            })
        try:
            Influx.write_points(data_queue)
            data_queue = []
        except Exception as e:
            print("Exception", e)
        delay = 10 - (time.time()-now)
        if delay > 0:
            time.sleep(delay)

#########################
