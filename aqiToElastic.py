#!/usr/bin/python
# coding=utf-8
# "DATASHEET": http://cl.ly/ekot
# https://gist.github.com/kadamski/92653913a53baf9dd1a8
from __future__ import print_function
import serial, struct, sys, time, json
from json import encoder    

import aqi
import pyhue
from phue import Bridge
from decimal import Decimal
from elasticsearch import Elasticsearch 
from datetime import datetime
import paho.mqtt.client as paho

encoder.FLOAT_REPR = lambda o: format(o, '.2f')

def on_connect(client, userdata, flags, rc):
    print("CONNACK received with code %d." % (rc))

client = paho.Client()
client.on_connect = on_connect
client.connect('172.104.235.199')

if sys.version_info[0] == 3:
    from urllib.request import urlopen
else:
    # Not Python 3 - today, it is most likely to be Python 2
    # But note that this might need an update when Python 4
    # might be around one day
    from urllib import urlopen
    
import xml.etree.ElementTree as ET 
import requests


DEBUG = 0
CMD_MODE = 2
CMD_QUERY_DATA = 4
CMD_DEVICE_ID = 5
CMD_SLEEP = 6
CMD_FIRMWARE = 7
CMD_WORKING_PERIOD = 8
MODE_ACTIVE = 0
MODE_QUERY = 1

BLYNK_AUTH='66c23a93de9846aa9cbaf58d8d19dd8f'
#blynk = blynklib.Blynk(BLYNK_AUTH)


ser = serial.Serial()
ser.port = "/dev/ttyUSB0"
ser.baudrate = 9600

ser.open()
ser.flushInput()

byte, data = 0, ""

def setDeckColor(aqi):
    bridge = Bridge('10.0.0.1')
    light_names = bridge.get_light_objects('name')
    green = 24267
    yellow = 10187
    orange = 6792
    red = 65386
    purple = 55524
    
    bridge.set_light('Deck', 'bri', 50, transitiontime=1)
    
    if aqi < 20:    
        bridge.set_light('Deck', 'on', False)
    elif aqi < 50:  
        bridge.set_light('Deck', 'on', True)  
        light_names["Deck"].hue = green
    elif aqi < 150:
        bridge.set_light('Deck', 'on', True)
        light_names["Deck"].hue = yellow    
    elif aqi < 175:
        bridge.set_light('Deck', 'on', True)
        light_names["Deck"].hue = green    
    elif aqi < 200:
        bridge.set_light('Deck', 'on', True)
        light_names["Deck"].hue = red 
 
def setDeckColorSolar(xray):
    bridge = Bridge('10.0.0.1')
    light_names = bridge.get_light_objects('name')
    green = 24267
    yellow = 10187
    orange = 6792
    red = 65386
    purple = 55524
    
    bridge.set_light('Deck', 'bri', 60, transitiontime=1)
    
    if xray < 50:    
        bridge.set_light('Deck', 'on', False)
        light_names["Deck"].hue = green
    elif xray < 100:  
        bridge.set_light('Deck', 'on', True)  
        light_names["Deck"].hue = green
    elif xray < 150:  
        bridge.set_light('Deck', 'on', True)  
        light_names["Deck"].hue = yellow
    elif xray < 200:  
        bridge.set_light('Deck', 'on', True)  
        light_names["Deck"].hue = orange
    elif aqi < 300:
        bridge.set_light('Deck', 'on', True)
        light_names["Deck"].hue = red    
                   
def dump(d, prefix=''):
    print(prefix + ' '.join(x.encode('hex') for x in d))

def construct_command(cmd, data=[]):
    assert len(data) <= 12
    data += [0,]*(12-len(data))
    checksum = (sum(data)+cmd-2)%256
    ret = "\xaa\xb4" + chr(cmd)
    ret += ''.join(chr(x) for x in data)
    ret += "\xff\xff" + chr(checksum) + "\xab"

    if DEBUG:
        dump(ret, '> ')
    return ret

def process_data(d):
    r = struct.unpack('<HHxxBB', d[2:])
    pm25 = r[0]/10.0
    pm10 = r[1]/10.0
    checksum = sum(ord(v) for v in d[2:8])%256
    return [pm25, pm10]

def process_version(d):
    r = struct.unpack('<BBBHBB', d[3:])
    checksum = sum(ord(v) for v in d[2:8])%256
    print("Y: {}, M: {}, D: {}, ID: {}, CRC={}".format(r[0], r[1], r[2], hex(r[3]), "OK" if (checksum==r[4] and r[5]==0xab) else "NOK"))

def read_response():
    byte = 0
    while byte != "\xaa":
        byte = ser.read(size=1)

    d = ser.read(size=9)

    if DEBUG:
        dump(d, '< ')
    return byte + d

def cmd_set_mode(mode=MODE_QUERY):
    ser.write(construct_command(CMD_MODE, [0x1, mode]))
    read_response()

def cmd_query_data():
    ser.write(construct_command(CMD_QUERY_DATA))
    d = read_response()
    values = []
    if d[1] == "\xc0":
        values = process_data(d)
    return values

def cmd_set_sleep(sleep=1):
    mode = 0 if sleep else 1
    ser.write(construct_command(CMD_SLEEP, [0x1, mode]))
    read_response()

def cmd_set_working_period(period):
    ser.write(construct_command(CMD_WORKING_PERIOD, [0x1, period]))
    read_response()

def cmd_firmware_ver():
    ser.write(construct_command(CMD_FIRMWARE))
    d = read_response()
    process_version(d)

def cmd_set_id(id):
    id_h = (id>>8) % 256
    id_l = id % 256
    ser.write(construct_command(CMD_DEVICE_ID, [0]*10+[id_l, id_h]))
    read_response()

def cToF(f):
    celsius = round((f - 32) * 5/9,2)
    return celsius

def getSolar():
    url = "https://www.hamqsl.com/solarxml.php"
    data = requests.get(url)
    root = ET.fromstring(data.content)
    #for child in root.iter('*'):
    #    print(child.tag)
    for tag in root.iter('solarflux'):
        solarflux=int(tag.text)
        print("solarflux:", solarflux)
    return solarflux

if __name__ == "__main__":
        client.loop_start()
         
        xray=getSolar()
        singleEnv = {}
        url = 'https://api.ecowitt.net/api/v3/device/real_time?application_key=971DEB582CFA59049B166125BB9DEF1B&api_key=009d974f-d4ae-4d61-ac9d-35306e2e2c67&mac=C4:5B:BE:6D:E3:44&call_back=all'
        data = urlopen(url).read()
        #print(data)
        d = json.loads(data)
        singleEnv['source'] = "dornbirn"
        singleEnv['xray'] = Decimal(xray)
        singleEnv['tempf'] = Decimal(d["data"]["outdoor"]["temperature"]["value"])
        singleEnv['tempc'] = cToF(Decimal(d["data"]["outdoor"]["temperature"]["value"]))
        singleEnv['bar'] = round(Decimal(d["data"]["pressure"]["relative"]["value"])* Decimal(33.8639), 1)
        singleEnv['hum'] = Decimal(d["data"]["outdoor"]["humidity"]["value"])
        singleEnv['rain_hourly'] = Decimal(d["data"]["rainfall"]["hourly"]["value"])
        singleEnv['rain_daily'] = Decimal(d["data"]["rainfall"]["daily"]["value"])
        singleEnv['rain_rate'] = Decimal(d["data"]["rainfall"]["rain_rate"]["value"])
        singleEnv['wind_dir'] = Decimal(d["data"]["wind"]["wind_direction"]["value"])
        singleEnv['wind_gust'] = Decimal(d["data"]["wind"]["wind_gust"]["value"])
        singleEnv['fridgeT'] = cToF(Decimal(d["data"]["temp_and_humidity_ch2"]["temperature"]["value"]))
        singleEnv['freezerT'] = cToF(Decimal(d["data"]["temp_and_humidity_ch3"]["temperature"]["value"]))
	#�singleEnv['soilCh1']= Decimal(d["data"]["soil_ch2"]["soilmoisture"]["value"])
        cmd_set_sleep(0)
        cmd_set_mode(1);
        
        es = Elasticsearch(
                ['http://172.104.235.199'],
                port=59200,
                )
        
        for t in range(10):
            values = cmd_query_data();
            if values is not None:
                singleEnv["PM2.5"] = values[0]
                singleEnv["PM10"] = values[1]
                singleEnv["aqi_2_5"] = aqi.to_iaqi(aqi.POLLUTANT_PM25, str(values[0]))
                singleEnv["aqi_10"] = aqi.to_iaqi(aqi.POLLUTANT_PM10, str(values[1]))
                singleEnv["compositeAQI"] = aqi.to_aqi([(aqi.POLLUTANT_PM25, str(values[0])), (aqi.POLLUTANT_PM10, str(values[1]))])
                singleEnv['timestamp'] = datetime.now().isoformat()
                
                #setDeckColor(singleEnv["compositeAQI"])
                setDeckColorSolar(xray)
                
                if values[0] > 0:
                    es.index(index='sds2', body=singleEnv)
                    client.publish("fjblau/env/pm2.5", str(singleEnv["compositeAQI"]) , qos=1)
                    client.publish("fjblau/env/xray", str(singleEnv["xray"]) , qos=1)

                    print(singleEnv)
                time.sleep(2)
        
        

        print("Going to sleep for 5min...")
        cmd_set_mode(0);
        cmd_set_sleep()
        time.sleep(5)

