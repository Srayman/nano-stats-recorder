#!/usr/bin/env python3

import asyncio
import argparse
import json
import csv
import os
# importing the requests library 
# pip install requests
import requests 
import time
import datetime
import statistics
from collections import defaultdict
from sys import exit
from time import sleep
from datetime import datetime
from datetime import timedelta

parser = argparse.ArgumentParser()
parser.add_argument('-host', '--node_url', type=str, help='Nano node url', default='localhost')
parser.add_argument('-port', '--node_port', type=str, help='Nano node port', default='55000')
parser.add_argument('-save', '--save', type=int, help='Save blocks to disk how often (in seconds) should be multiple of --delay', default=180)
parser.add_argument('-delay', '--delay', type=int, help='recorder delay (in seconds)', default=15)
args = parser.parse_args()

json_data = []
timeString = (datetime.utcnow() + timedelta(hours=2)).strftime("%Y-%m-%d")
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
    data1 = {'action':'active_difficulty','include_trend': 'true'}
    data2 = {'action':'confirmation_active'}
    data3 = {'action':'stats','type':'objects'}
    data4 = {'action':'block_count','include_cemented':'true'}
    data5 = {'action':'confirmation_quorum'}
    data6 = {'action':'bootstrap_status'}

    while 1:
        filename2 = 'stats_'+(datetime.utcnow() + timedelta(hours=2)).strftime("%Y-%m-%d")+'.json'
        if filename2 != filename:
            writeBkup()
            timeString = (datetime.utcnow() + timedelta(hours=2)).strftime("%Y-%m-%d")
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
            r5 = requests.post(url = URL, json = data5)
            r6 = requests.post(url = URL, json = data6)
            # extracting data in json format 
            response = r.json()
            response2 = r2.json()
            response3 = r3.json()
            response4 = r4.json()
            response5 = r5.json()
            response6 = r6.json()
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
            data['difficulty_trend_min'] = str(min(map(float,response['difficulty_trend'])))
            data['difficulty_trend_max'] = str(max(map(float,response['difficulty_trend'])))
            data['difficulty_trend_median'] = str(statistics.median(map(float,response['difficulty_trend'])))
            data['difficulty_trend_mean'] = str(statistics.mean(map(float,response['difficulty_trend'])))
            data['alarm_operations_count'] = response3['node']['alarm']['operations']['count']
            data['ledger_bootstrap_weights_count'] = response3['node']['ledger']['bootstrap_weights']['count']
            data['active_roots_count'] = response3['node']['active']['roots']['count']
            data['active_blocks_count'] = response3['node']['active']['blocks']['count']
            data['active_confirmed_count'] = response3['node']['active']['confirmed']['count']
            data['active_cementable_count'] = response3['node']['active']['priority_cementable_frontiers_count']['count']
            data['tcp_channels_count'] = response3['node']['tcp_channels']['channels']['count']
            data['tcp_channels_attempts_count'] = response3['node']['tcp_channels']['attempts']['count']
            data['response_channels_count'] = response3['node']['response_channels']['channels']['count']
            data['vote_processor_count'] = response3['node']['vote_processor']['votes']['count']
            data['vote_processor_rep1'] = response3['node']['vote_processor']['representatives_1']['count']
            data['vote_processor_rep2'] = response3['node']['vote_processor']['representatives_2']['count']
            data['vote_processor_rep3'] = response3['node']['vote_processor']['representatives_3']['count']
            data['block_processor_state'] = response3['node']['block_processor']['state_blocks']['count']
            data['block_processor_blocks'] = response3['node']['block_processor']['blocks']['count']
            data['block_processor_hashes'] = response3['node']['block_processor']['blocks_hashes']['count']
            data['block_processor_forced'] = response3['node']['block_processor']['forced']['count']
            data['block_processor_rolled_back'] = response3['node']['block_processor']['rolled_back']['count']
            data['block_processor_generator'] = response3['node']['block_processor']['generator']['state_blocks']['count']
            data['block_arrival_count'] = response3['node']['block_arrival']['arrival']['count']
            data['online_reps_arrival_count'] = response3['node']['online_reps']['arrival']['count']
            data['votes_cache_count'] = response3['node']['votes_cache']['cache']['count']
            data['block_uniquer_count'] = response3['node']['block_uniquer']['blocks']['count']
            data['vote_uniquer_count'] = response3['node']['vote_uniquer']['votes']['count']
            data['confirmation_height_count'] = response3['node']['pending_confirmation_height']['pending']['count']
            data['block_count'] = response4['count']
            data['unchecked_count'] = response4['unchecked']
            data['cemented_count'] = response4['cemented']
            data['quorum_delta'] = response5['quorum_delta']
            data['online_weight_minimum'] = response5['online_weight_minimum']
            data['online_stake_total'] = response5['online_stake_total']
            data['peers_stake_total'] = response5['peers_stake_total']
            data['peers_stake_required'] = response5['peers_stake_required']
            if 'clients' in response6:
                data['bootstrap_clients'] = response6['clients']
                data['bootstrap_pulls'] = response6['pulls']
                data['bootstrap_pulling'] = response6['pulling']
                data['bootstrap_connections'] = response6['connections']
                data['bootstrap_target_connections'] = response6['target_connections']
                data['bootstrap_total_blocks'] = response6['total_blocks']
                data['bootstrap_lazy_pulls'] = response6['lazy_pulls']
            else:
                data['bootstrap_clients'] = '0'
                data['bootstrap_pulls'] = '0'
                data['bootstrap_pulling'] = '0'
                data['bootstrap_connections'] = '0'
                data['bootstrap_target_connections'] = '0'
                data['bootstrap_total_blocks'] = '0'
                data['bootstrap_lazy_pulls'] = '0'
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