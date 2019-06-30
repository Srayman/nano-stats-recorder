#!/usr/bin/env python3

import asyncio
import argparse
import json
import csv
import os
# importing the requests library 
# pip install requests
import requests 
import json
import time
import datetime
from collections import defaultdict
from sys import exit
from time import sleep
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument('-host', '--node_url', type=str, help='Nano node url', default='localhost')
parser.add_argument('-port', '--node_port', type=str, help='Nano node port', default='55000')
parser.add_argument('-save', '--save', type=int, help='Save blocks to disk how often (in seconds) should be multiple of --delay', default=60)
parser.add_argument('-delay', '--delay', type=int, help='recorder delay (in seconds)', default=15)
args = parser.parse_args()

json_data = []
timeString = datetime.utcnow().strftime("%Y-%m-%d")
filename = 'stats_'+timeString+'.json'
#Rename existing file
try:
    os.rename('stats.json','stats.json.'+datetime.utcnow().strftime("%Y%m%d%H%M%S"))
    print('Renaming stats.json ...')
except:
    print('stats.json does not exist, create new file ...')

def writeBkup():
    global json_data
    global filename
    print('Writing to '+filename+' ...')
    try:
        with open(filename, 'w') as jsonfile:
            jsonfile.write(json.dumps(json_data))
    except:
        print('unable to write to file ...')

async def main():
    global json_data
    global filename
    global timeString
    try:
        with open(filename) as jsonfile:
            json_data = json.load(jsonfile)
    except:
        print(filename+' does not exist, create new file ...')
    loop_count = 0
    # api-endpoint 
    URL = "http://"+args.node_url+":"+args.node_port
    print("Connecting to: "+URL)

    # defining a params dict for the parameters to be sent to the API 
    data1 = {'action':'active_difficulty'}
    data2 = {'action':'confirmation_active'}
    data3 = {'action':'stats','type':'objects'}
    data4 = {'action':'block_count','include_cemented':'true'}

    while 1:
        filename2 = 'stats_'+datetime.utcnow().strftime("%Y-%m-%d")+'.json'
        if filename2 != filename:
            writeBkup()
            timeString = datetime.utcnow().strftime("%Y-%m-%d")
            json_data = []
            filename = filename2
        loop_count += 1
        currentTime = time.time()
        # sending get request and saving the response as response object 
        try:
            r = requests.post(url = URL, json = data1)
            r2 = requests.post(url = URL, json = data2)
            r3 = requests.post(url = URL, json = data3)
            r4 = requests.post(url = URL, json = data4)
            # extracting data in json format 
            response = r.json()
            response2 = r2.json()
            response3 = r3.json()
            response4 = r4.json()
        except:
            print("Error connecting to RPC server. Make sure you have enabled it in ~/Nano/config.json and check "
          "./sample_client.py --help")
#        print(response2)
        try:
            data = {}
            data['timestamp'] = str(time.time())
            data['confirmation_active'] = str(len(response2['confirmations']))
            data['network_minimum'] = response['network_minimum']
            data['network_current'] = response['network_current']
            data['multiplier'] = response['multiplier']
            data['confirmation_height_count'] = response3['node']['pending_confirmation_height']['pending']['count']
            data['block_count'] = response4['count']
            data['unchecked_count'] = response4['unchecked']
            data['cemented_count'] = response4['cemented']
            json_data.append(data)
        except Exception as e: print(e)
#            print('\nAn error occurred getting data')
        if loop_count%(round(args.save/args.delay)) == 0:
            writeBkup()
        endTime = time.time()
        print('{} records - '.format(len(json_data))+'Time to Process: '+str(endTime-currentTime)+' - Active Confirmations: '+str(len(response2['confirmations'])))
        if (args.delay-(endTime - currentTime)) < 0:
            sleep(0)
        else:
            sleep(args.delay-(endTime - currentTime))

try:
    asyncio.get_event_loop().run_until_complete(main())
except KeyboardInterrupt:
    pass

print('\nWriting to stats.json .....')
with open('stats.json', 'w') as jsonfile:
    jsonfile.write(json.dumps(json_data))
print('Done')