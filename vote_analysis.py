#!/usr/bin/env python3
import traceback
import asyncio
import websockets
import argparse
import json
import csv
import os
# importing the requests library 
# pip install requests
#import requests 
import time
import datetime
import statistics
import aiohttp
import math
import config
import copy
import ujson
#from aiohttp_requests import requests
from collections import defaultdict
from sys import exit
from time import sleep
from datetime import datetime
from aiofile import AIOFile

parser = argparse.ArgumentParser()
parser.add_argument('-host', '--node_url', type=str, help='Nano node url', default=config.host)
parser.add_argument('-port', '--node_port', type=str, help='Nano node port', default=config.port)
parser.add_argument('-socket', '--socket_port', type=str, help='Nano Websocket port', default=config.socket)
parser.add_argument('-save', '--save', type=int, help='Save data to disk how often (number of blocks)', default=config.save)
parser.add_argument('-delay', '--delay', type=int, help='Sending delay (in seconds)', default=config.delay)
parser.add_argument('-send', '--send', type=str, help='Send/Receive use true (default false)', default=config.send)
parser.add_argument('-beta', '--beta', type=str, help='Is this the beta network?  (default true)', default='true')
parser.add_argument('-vbh', '--vbh', type=int, help='Time interval (in seconds) for vote by hash recording', default=60)
args = parser.parse_args()

if args.send == 'true':
    if args.beta == 'true':
        wallet = config.betawallet
        account = config.betaaccount
    else:
        wallet = config.wallet
        account = config.account
else:
    if args.beta == 'true':
        account = config.betamonitor
    else:
        account = config.monitor

timeString = datetime.utcnow().strftime("%Y-%m-%d")

VOTE_BY_HASH_MAX = 12
votes = defaultdict(lambda: [0]*VOTE_BY_HASH_MAX)

VOTE_COUNT_MAX = 200
counts = defaultdict(lambda: [0]*VOTE_COUNT_MAX)

print("################################################")
print("#       TO QUIT - USE CTRL-C ONLY ONCE         #")
print("# THEN WAIT SEVERAL SECONDS FOR FILES TO WRITE #")
print("################################################")
#Rename existing file
try:
    os.rename('votes.json','votes.json.'+datetime.utcnow().strftime("%Y%m%d%H%M%S"))
    print('Renaming votes.json ...')
except:
    print('votes.json does not exist, create new file ...')
try:
    os.rename('vote_hashes.json','vote_hashes.json.'+datetime.utcnow().strftime("%Y%m%d%H%M%S"))
    print('Renaming vote_hashes.json ...')
except:
    print('vote_hashes.json does not exist, create new file ...')
try:
    os.rename('vote_data.json','vote_data.json.'+datetime.utcnow().strftime("%Y%m%d%H%M%S"))
    print('Renaming vote_data.json ...')
except:
    print('vote_data.json does not exist, create new file ...')
try:
    os.rename('vote_batching.csv','vote_batching.csv.'+datetime.utcnow().strftime("%Y%m%d%H%M%S"))
    print('Renaming vote_batching.csv ...')
except:
    print('vote_batching.csv does not exist, create new file ...')
try:
    os.rename('vote_counts.csv','vote_counts.csv.'+datetime.utcnow().strftime("%Y%m%d%H%M%S"))
    print('Renaming vote_counts.csv ...')
except:
    print('vote_counts.csv does not exist, create new file ...')

def subscription(topic: str, ack: bool=False, options: dict=None):
    d = {"action": "subscribe", "topic": topic, "ack": ack}
    if options is not None:
        d["options"] = options
    return d

def receiverpc(account, hash, work):
    return {'action':'receive', 'wallet':wallet, 'account':account, 'block':hash, 'work':work}

def sendrpc(account, work):
    return {'action':'send', 'wallet':wallet, 'source':account,'destination':account,'amount':'1', 'work':work}

def blockcreate(account, representative, balance, link, previous, work):
    return {'action':'block_create', 'type':'state', 'balance':balance, 'wallet':wallet, 'account':account, 'representative':representative, 'link':link, 'previous':previous, 'work':work}

def process(block):
    return {'action':'process', 'block':block, 'watch_work':'false'}
    
def republish(hash):
    return {'action':'republish', 'hash':hash}
    
def confirm(hash):
    return {'action':'block_confirm', 'hash':hash}

def accountrpc(account):
    return {'action':'account_history', 'account':account, 'count':'1'}

def accountbalance(account):
    return {'action':'account_balance', 'account':account}
	
def pending(account):
    return {'action':'pending', 'account':account, 'count':'1', 'include_active':'true'}

def workget(account):
    return {'action':'work_get', 'wallet':wallet, 'account':account}
    
def workgenerate(hash,account):
    return {'action':'work_generate', 'hash':hash, 'use_peers':'false'}
    
def dpowworkget(hash, account):
    return {'hash':hash, 'user':config.dpow_user, 'api_key':config.dpow_api_key, 'account':account}

async def getWork(self, hash, account):
    if config.dpow_enable == 'true':
        async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
            res = await session.post(config.dpow_url, json=dpowworkget(hash, account))
            res_js = await res.json()
            if 'work' not in res_js: print(res_js)
            self.work = res_js["work"]
    else:
        async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
            res = await session.post(f"http://{args.node_url}:{args.node_port}", json=workgenerate(hash,account))
            res_js = await res.json()
            if 'work' not in res_js: print(res_js)
            self.work = res_js["work"]

class VoteAnalysis():
    def __init__(self):
        self.vote_data_copy = []
        self.vote_data = []
        self.conf_data = []
        self.hashes = []
        self.confirmedHashes = []
        self.vote_by_hash = {}
        self.vbh = defaultdict(lambda: [0]*VOTE_BY_HASH_MAX)
        self.block_data = defaultdict(dict)
        self.hash = ''
        self.work = None
        self.balance = None
        self.pending = None
        self.timestamp = None

    def recordVBH(self):
        self.vote_by_hash[str(time.time())] = self.vbh
        self.vbh = defaultdict(lambda: [0]*VOTE_BY_HASH_MAX)
        
    async def writeBkup(self):
        print(str(time.time())+' - processing votes')
# Enable votes.json for debugging all votes compared to filtered votes
#        print(str(time.time())+' - Writing to votes.json .....')
#        with open('votes.json', 'a') as jsonfile:
#            jsonfile.write(json.dumps(self.vote_data))
        beforeTime = time.time()
        print(str(time.time())+' - {} votes received'.format(len(self.vote_data_copy)))
        for x in self.vote_data_copy:
            for z in x['blocks']:
                if z in self.hashes:
                    data = {}
                    data['time'] = x['time']
#                    data['account'] = x['account']
#                    data['blocks'] = x['blocks']
                    data['count'] = 1
                    if z in self.block_data:
                        if x['account'] in self.block_data[z]:
                            data['count'] = self.block_data[z][x['account']]['count']+1
                            data['time'] = self.block_data[z][x['account']]['time']
                    self.block_data[z][x['account']] = data
        print(str(time.time())+' - '+str(len(self.block_data[self.hash]))+" votes for Hash: "+self.hash)
        print("")
        afterTime = time.time()
        print('For Loop Time: '+str(afterTime-beforeTime))
        if len(self.conf_data)%args.save == 0:
            print('\nWriting to vote_hashes.json .....')
            async with AIOFile("vote_hashes.json", 'w+') as jsonfile:
                await jsonfile.write(json.dumps(analysis.conf_data))
                await jsonfile.fsync()
#            with open('vote_hashes.json', 'w') as jsonfile:
#                jsonfile.write(json.dumps(analysis.conf_data))
            print('\nWriting to vote_data.json .....')
            async with AIOFile("vote_data.json", 'w+') as jsonfile:
                await jsonfile.write(json.dumps(analysis.block_data))
                await jsonfile.fsync()
#            with open('vote_data.json', 'w') as jsonfile:
#                jsonfile.write(json.dumps(analysis.block_data))    

# Only monitor specified account for blocks and votes
    async def monitor_send(self):
        block_count = 0
        while 1:
            self.timestamp = math.floor(time.time()*1000)
            if len(self.hashes) > block_count or len(self.vote_data) > 10000:
                block_count = len(self.hashes)
                if len(self.hashes) >= 1:
                    self.hash = self.hashes[-1]
                copyTime = time.time()
                self.vote_data_copy = ujson.loads(ujson.dumps(self.vote_data))
                self.vote_data = []
                copyTimeEnd = time.time()
                writeTime = time.time()
                asyncio.create_task(self.writeBkup())
                writeTimeEnd = time.time()
                print('Copy Time: '+str(copyTimeEnd-copyTime)+' - Write Bkup Time: '+str(writeTimeEnd-writeTime))
                print('Total Time: '+str(writeTimeEnd-copyTime))
            else:
                print("Hash Not Confirmed")
            await asyncio.sleep(args.delay+1)

# Periodic send/receive to capture votes
    async def periodic_send(self):
        res_js = ''
        async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
            res = await session.post(f"http://{args.node_url}:{args.node_port}", json=accountrpc(account))
            res_js = await res.json()
        self.hash = res_js['history'][0]['hash']
        if res_js['history'][0]['type'] == 'send':
            send = 0
            self.pending = res_js['history'][0]['amount']
        else:
            send = 1
        async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
            res = await session.post(f"http://{args.node_url}:{args.node_port}", json=accountbalance(account))
            res_js = await res.json()
        self.balance = res_js['balance']
        while 1:
            if self.hash in self.hashes or self.timestamp == None:
                if self.hashes: 
                    self.vote_data_copy = ujson.loads(ujson.dumps(self.vote_data))
                    self.vote_data = []
                    asyncio.create_task(self.writeBkup())
                try:
                    await getWork(self, self.hash, account)
                    self.timestamp = math.floor(time.time()*1000)
                    if send == 1:
                        print(str(time.time())+' - Sending ... Work: '+self.work)
                        self.balance = int(self.balance)-1
                        async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
                            res = await session.post(f"http://{args.node_url}:{args.node_port}", json=blockcreate(account, config.representative, self.balance, account, self.hash, self.work))
                            res_js = await res.json()
                            if 'hash' in res_js:
                                async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
                                    res = await session.post(f"http://{args.node_url}:{args.node_port}", json=process(res_js['block']))
                                    res_js = await res.json()
                                    if 'hash' in res_js:
                                        self.hash = res_js['hash']
                                        self.hashes.append(self.hash)
                                        send = 0
                                    else:
                                        print(res_js)
                                        print(blockcreate(account, config.representative, self.balance, account, self.hash, self.work))
                            else:
                                print(res_js)
#                        async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
#                            res = await session.post(f"http://{args.node_url}:{args.node_port}", json=sendrpc(account, self.work))
#                            res_js = await res.json()
#                            if 'block' in res_js:
#                                self.hash = res_js["block"]
#                                self.hashes.append(self.hash)
#                                send = 0
#                            else: 
#                                print(res_js)
                    else:
                        print(str(time.time())+' - Receiving ... Work: '+self.work)
                        self.balance = int(self.balance)+1
                        async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
                            res = await session.post(f"http://{args.node_url}:{args.node_port}", json=blockcreate(account, config.representative, self.balance, self.hash, self.hash, self.work))
                            res_js = await res.json()
                            if 'hash' in res_js:
                                async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
                                    res = await session.post(f"http://{args.node_url}:{args.node_port}", json=process(res_js['block']))
                                    res_js = await res.json()
                                    if 'hash' in res_js:
                                        self.hash = res_js['hash']
                                        self.hashes.append(self.hash)
                                        send = 1
                                    else:
                                        print(res_js)
                            else:
                                print(res_js)
#                        async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
#                            res = await session.post(f"http://{args.node_url}:{args.node_port}", json=receiverpc(account, self.hash, self.work))
#                            res_js = await res.json()
#                            if 'block' in res_js:
#                                self.hash = res_js["block"]
#                                self.hashes.append(self.hash)
#                                send = 1
#                            else: 
#                                print(res_js)
                except Exception as e: 
                    print("Error Sending or Receiving")
                    print(traceback.format_exc())
                    print(res_js)
                print(str(time.time())+" - Hash: "+self.hash)
            else:
                print("Hash Not Confirmed")
#                async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
#                    res = await session.post(f"http://{args.node_url}:{args.node_port}", json=confirm(self.hash))
#                    res_js = await res.json()
#                    print(res_js)
            await asyncio.sleep(args.delay)
#"all_local_accounts": "true", 
    async def analyse_votes(self):
        async with websockets.connect(f"ws://{args.node_url}:{args.socket_port}") as websocket:
            await websocket.send(json.dumps(subscription("confirmation", ack=True, 
                options={"accounts":[account],
                         "confirmation_type": "active_quorum",
                         "include_election_info": "true"})))
            
# Use the following instead of above to listen on all accounts instead of filtered account
#            await websocket.send(json.dumps(subscription("confirmation", ack=True, 
#                options={"confirmation_type": "active_quorum",
#                        "include_election_info": "true",
#                        "include_block": "false"
#                })))

            print(await websocket.recv())  # ack
        
            await websocket.send(json.dumps(subscription("vote", ack=True)))
            print(await websocket.recv())  # ack
        
            blocks = set()
            block_count = 0
            vbhInterval = time.time()
            while 1:
                if time.time() - vbhInterval > args.vbh:
                    print('recording vbh')
                    vbhInterval = time.time()
                    self.recordVBH()
                if not websocket.open:
                    print ('Websocket NOT connected. Trying to reconnect.')
                    try:
                        websocket = await asyncio.wait_for(websockets.connect(f"ws://{args.node_url}:{args.socket_port}"), 2)
                        await websocket.send(json.dumps(subscription("confirmation", ack=True, 
                            options={"accounts":[account], 
                                     "confirmation_type": "active_quorum",
                                     "include_election_info": "true"})))
# Use the following instead of above to listen on all accounts instead of filtered account
#                        await websocket.send(json.dumps(subscription("confirmation", ack=True, 
#                            options={"confirmation_type": "active_quorum",
#                                    "include_election_info": "true",
#                                    "include_block": "false"
#                            })))
                        await websocket.send(json.dumps(subscription("vote", ack=True,
                            options={"include_replays": "true",
                                    "include_indeterminate": "true"
                            })))
                    except Exception as e:
                        print('Error!: ', e)
                try: 
                    rec = json.loads(await websocket.recv())
#                    print(json.dumps(rec))
                    topic = rec.get("topic", None)
                    if topic:
                        message = rec["message"]
                        if topic == "vote":
                            timeMilli = int(time.time()*1000)
                            if timeMilli-int(rec['time']) > 500:
                                print('Time: '+str(timeMilli)+' - Vote Time: '+rec['time']+' - Diff: '+str(timeMilli-int(rec['time'])))
                            repaccount, vote_count = message["account"], len(message["blocks"])
                            votes[repaccount][vote_count-1] += 1
                            self.vbh[repaccount][vote_count-1] += 1
                            data = {}
                            data['time'] = rec['time']
                            data['account'] = message['account']
                            data['sequence'] = message['sequence']
                            data['blocks'] = message['blocks']
                            self.vote_data.append(data)
                        elif topic == "confirmation":
                            data = {}
                            data['timestamp'] = self.timestamp
                            data['time'] = rec['time']
                            data['conf_time'] = message['election_info']['time']
                            data['account'] = message['account']
                            data['hash'] = message['hash']
                            data['confirmation_type'] = message['confirmation_type']
                            self.conf_data.append(data)
                            self.confirmedHashes.append(message['hash'])
                            if args.send != 'true':
                                self.hashes.append(message['hash'])
                            print("{} - {} blocks sent".format(str(time.time()), len(self.hashes)))
                            print("{} - {} blocks confirmed".format(str(time.time()), len(self.conf_data))) 
                except Exception as e:
                    print('Error!: ', e)

analysis = VoteAnalysis()
try:
    if args.send == 'true':
        asyncio.get_event_loop().run_until_complete(asyncio.gather(
            analysis.periodic_send(),
            analysis.analyse_votes()
        ))
    else:
        asyncio.get_event_loop().run_until_complete(asyncio.gather(
            analysis.monitor_send(),
            analysis.analyse_votes()
        ))
except ConnectionRefusedError:
    print("Error connecting to websocket server. Make sure you have enabled it in ~/Nano/config.json and check "
          "./sample_client.py --help")
    exit(1)
except KeyboardInterrupt:
    pass

#analysis.writeBkup()
analysis.recordVBH()
print('\nWriting to vote_hashes.json .....')
with open('vote_hashes.json', 'w') as jsonfile:
    jsonfile.write(json.dumps(analysis.conf_data))
print('\nWriting to vote_data.json .....')
with open('vote_data.json', 'w') as jsonfile:
    jsonfile.write(json.dumps(analysis.block_data))
print('\nWriting to vbh_interval.json .....')
with open('vbh_interval.json', 'w') as jsonfile:
    jsonfile.write(json.dumps(analysis.vote_by_hash))
vote_dict = dict(votes)
print('\nWriting to vote_batching.csv .....')
with open('vote_batching.csv', 'w') as csvfile:
    #csv_columns = ['Rep Address','1 votes','2 votes''3 votes','4 votes','5 votes','6 votes','7 votes','8 votes','9 votes','10 votes','11 votes','12 votes']
    for k, v in vote_dict.items():
        line = k+","
        for value in v:
            line = line+str(value)+","
        line = line[:-1]+"\n"
        csvfile.write(line)
print('\nWriting to vote_counts.csv .....')
with open('vote_counts.csv', 'w') as csvfile:
    #csv_columns = ['Rep Address','1 count','2 count', ... '60 count']
    for block in analysis.block_data:
        for reps in analysis.block_data[block]:
            counts[reps][analysis.block_data[block][reps]['count']-1] += 1
    count_dict = dict(counts)
    for k, v in count_dict.items():
        line = k+","
        for value in v:
            line = line+str(value)+","
        line = line[:-1]+"\n"
        csvfile.write(line)
print('Done')
