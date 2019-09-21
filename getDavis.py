#! /Library/Frameworks/Python.framework/Versions/3.7/bin/python3

import sys

if sys.version_info[0] == 3:
    from urllib.request import urlopen
else:
    # Not Python 3 - today, it is most likely to be Python 2
    # But note that this might need an update when Python 4
    # might be around one day
    from urllib import urlopen

import json
import paho.mqtt.client as paho
import time
 
import pyhue

from elasticsearch import Elasticsearch 

from datetime import datetime
import pytz

def on_connect(client, userdata, flags, rc):
    print("CONNACK received with code %d." % (rc))
 
#client = paho.Client()
#client.on_connect = on_connect
#client.connect('192.168.0.182', 1883)
#client.loop_start()

while True:
	url = 'http://api.weatherlink.com/v1/NoaaExt.json?user=001D0A0100EE&pass=2Ellbelt!&apiToken=B1A41C82525B4BB7AB170F5915D7C316'
	data = urlopen(url).read()
	d = json.loads(data)
	outputString = {}
	outputString['timestamp'] = datetime.now().isoformat()
	outputString['tempf'] = (d["temp_c"])
	outputString['bar'] = (d["pressure_mb"])
	outputString['hum'] = (d["relative_humidity"])
	url = 'https://api.waqi.info/feed/feldkirch/?token=a7c24542659db44c96da7402aff64c8eec1a5dd1'
	data = urlopen(url).read()
	d2 = json.loads(data)
	outputString['aqi-feldkirch'] = (d2["data"]["iaqi"]["pm10"]["v"])
	outputString['no2-feldkirch'] = (d2["data"]["iaqi"]["no2"]["v"])
	url = 'https://api.waqi.info/feed/bregenz/?token=a7c24542659db44c96da7402aff64c8eec1a5dd1'
	data = urlopen(url).read()
	d2 = json.loads(data)
	outputString['aqi-bregenz'] = (d2["data"]["iaqi"]["pm10"]["v"])
	outputString['no2-bregenz'] = (d2["data"]["iaqi"]["no2"]["v"])
	#client.publish("test/wx", json.dumps(outputString), qos=1)

	es = Elasticsearch(
      ['http://172.104.235.199'],
      port=9200,
  )
	es.index(index='aqi', body=outputString)

	print(json.dumps(outputString))
	time.sleep(10)
