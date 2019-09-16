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
import upload
import config
from collections import defaultdict
from sys import exit
from time import sleep
from datetime import datetime
from datetime import timedelta

parser = argparse.ArgumentParser()
parser.add_argument('-host', '--node_url', type=str, help='Nano node url', default='localhost')
parser.add_argument('-port', '--node_port', type=str, help='Nano node port', default='55000')
parser.add_argument('-save', '--save', type=int, help='Save blocks to disk how often (in seconds) should be multiple of --delay', default=60)
parser.add_argument('-delay', '--delay', type=int, help='recorder delay (in seconds)', default=10)
parser.add_argument('-timeout', '--timeout', type=float, help='rpc request timeout (in seconds)', default=60)
args = parser.parse_args()

json_data = []
hashes = []
distinct = []
timeString = (datetime.utcnow() + timedelta(hours=0)).strftime("%Y-%m-%d")
filename = 'confirmation_history_'+timeString+'.json'
#Rename existing file
try:
    os.rename('confirmation_history.json','confirmation_history.json.'+datetime.utcnow().strftime("%Y%m%d%H%M%S"))
    print('Renaming confirmation_history.json ...')
except:
    print('confirmation_history.json does not exist, create new file ...')

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
    global hashes
    global distinct
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
    data = {'action':'confirmation_history'} 

    while 1:
        filename2 = 'confirmation_history_'+(datetime.utcnow() + timedelta(hours=0)).strftime("%Y-%m-%d")+'.json'
        if filename2 != filename:
            writeBkup()
            if config.upload == 'true':
                upload.upload(filename)
            writeString = timeString+'|'+str(len(json_data))+'\n'
            with open('files.txt', 'a') as files:
                files.write(writeString)
            timeString = (datetime.utcnow() + timedelta(hours=0)).strftime("%Y-%m-%d")
            json_data = []
            filename = filename2
        loop_count += 1
        currentTime = time.time()
        # sending get request and saving the response as response object 
        try:
            r = requests.post(url = URL, json = data, timeout=args.timeout) 
        
            # extracting data in json format 
            response = r.json()
        except:
            print("Error connecting to RPC server. Make sure you have enabled it in ~/Nano/config.json and check "
          "./sample_client.py --help")
#        print(response)
        try:
            json_data += response['confirmations']
            # To sort the list in place...
            json_data.sort(key=lambda x: x.get('time', 0), reverse=True)
            json_data = list({ each['hash'] : each for each in json_data }.values())
        except:
            print('\nAn error occurred getting data')		
        print('{} blocks confirmed - '.format(len(json_data))+"execution: %s seconds" % (time.time() - currentTime))
        if loop_count%(round(args.save/args.delay)) == 0:
            writeBkup()
        endTime = time.time()
        if (args.delay-(endTime - currentTime)) < 0:
            sleep(0)
        else:
            sleep(args.delay-(endTime - currentTime))

try:
    asyncio.get_event_loop().run_until_complete(main())
#except ConnectionRefusedError:
#    print("Error connecting to RPC server. Make sure you have enabled it in ~/Nano/config.json and check "
#          "./sample_client.py --help")
#    exit(1)
except KeyboardInterrupt:
    pass

json_data.sort(key=lambda x: x.get('time', 0), reverse=True)
json_data = list({ each['hash'] : each for each in json_data }.values())
# reformat data
confirmations = {'hashes':{}}
for item in json_data:
    hash = item['hash']
    confirmations['hashes'][hash] = item
#confirmations = json_data
print('{} distinct confirmations'.format(len(confirmations['hashes'])))
print('\nWriting to confirmation_history.json .....')
with open('confirmation_history.json', 'w') as jsonfile:
    jsonfile.write(json.dumps(json_data))
print('Done')