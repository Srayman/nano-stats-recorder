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
import mpmath
import copy
#from aiohttp_requests import requests
from collections import defaultdict
from sys import exit
from time import sleep
from datetime import datetime
from mpmath import mp

parser = argparse.ArgumentParser()
parser.add_argument('-host', '--node_url', type=str, help='Nano node url', default=config.host)
parser.add_argument('-port', '--node_port', type=str, help='Nano node port', default=config.port)
parser.add_argument('-socket', '--socket_port', type=str, help='Nano Websocket port', default=config.socket)
parser.add_argument('-save', '--save', type=int, help='Save data to disk how often (number of blocks)', default=config.save)
parser.add_argument('-delay', '--delay', type=int, help='Sending delay (in seconds)', default=config.delay)
parser.add_argument('-send', '--send', type=str, help='Send/Receive use true (default false)', default=config.send)
parser.add_argument('-beta', '--beta', type=str, help='Is this the beta network?  (default true)', default='true')
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
VOTE_COUNT_MAX = 60
counts = defaultdict(lambda: [0]*VOTE_COUNT_MAX)

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
    return {'action':'process', 'block':block}

def accountrpc(account):
    return {'action':'account_history', 'account':account, 'count':'1'}

def accountbalance(account):
    return {'action':'account_balance', 'account':account}
	
def pending(account):
    return {'action':'pending', 'account':account, 'count':'1', 'include_active':'true'}

def workget(account):
    return {'action':'work_get', 'wallet':wallet, 'account':account}

def dpowworkget(hash, account):
    return {'hash':hash, 'user':config.dpow_user, 'api_key':config.dpow_api_key, 'account':account}

async def getWork(self, hash, account):
    if config.dpow_enable == 'true':
        async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
            res = await session.post(config.dpow_url, json=dpowworkget(hash, account))
            res_js = await res.json()
            if not res_js["work"]: print(res_js)
            self.work = res_js["work"]
    else:
        async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
            res = await session.post(f"http://{args.node_url}:{args.node_port}", json=workget(account))
            res_js = await res.json()
            if not res_js["work"]: print(res_js)
            self.work = res_js["work"]

class VoteAnalysis():
    def __init__(self):
        self.vote_data = []
        self.conf_data = []
        self.hashes = []
        self.block_data = defaultdict(dict)
        self.hash = None
        self.work = None
        self.balance = None
        self.pending = None
        self.timestamp = math.floor(time.time()*1000)

    def writeBkup(self):
# Enable votes.json for debugging all votes compared to filtered votes
#        print(str(time.time())+' - Writing to votes.json .....')
#        with open('votes.json', 'a') as jsonfile:
#            jsonfile.write(json.dumps(self.vote_data))
        vote_data_copy = copy.deepcopy(self.vote_data)
        self.vote_data = []
        print(str(time.time())+' - {} votes received'.format(len(vote_data_copy)))
        for x in vote_data_copy:
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
        if len(self.conf_data)%args.save == 0:
            print('\nWriting to vote_hashes.json .....')
            with open('vote_hashes.json', 'w') as jsonfile:
                jsonfile.write(json.dumps(analysis.conf_data))
            print('\nWriting to vote_data.json .....')
            with open('vote_data.json', 'w') as jsonfile:
                jsonfile.write(json.dumps(analysis.block_data))    

# Only monitor specified account for blocks and votes
    async def monitor_send(self):
        block_count = 0
        while 1:
            self.timestamp = math.floor(time.time()*1000)
            if len(self.hashes) > block_count:
                block_count = len(self.hashes)
                self.hash = self.hashes[-1]
                self.writeBkup()
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
            if self.hash in self.hashes or not self.hashes:
                if self.hashes: self.writeBkup()
                try:
                    await getWork(self, self.hash, account)
                    self.timestamp = math.floor(time.time()*1000)
                    if send == 1:
                        print(str(time.time())+' - Sending ... Work: '+self.work)
                        self.balance = mp.nstr(mp.fsub(mp.mpmathify(self.balance),1),64)[:-2]
                        async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
                            res = await session.post(f"http://{args.node_url}:{args.node_port}", json=blockcreate(account, config.representative, self.balance, account, self.hash, self.work))
                            res_js = await res.json()
                            if 'hash' in res_js:
                                async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
                                    res = await session.post(f"http://{args.node_url}:{args.node_port}", json=process(res_js['block']))
                                    res_js = await res.json()
                                    if 'hash' in res_js:
                                        self.hash = res_js['hash']
                                        send = 0
                                    else:
                                        print(res_js)
                            else:
                                print(res_js)
#                        async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
#                            res = await session.post(f"http://{args.node_url}:{args.node_port}", json=sendrpc(account, self.work))
#                            res_js = await res.json()
#                            if 'block' in res_js:
#                                self.hash = res_js["block"]
#                                send = 0
#                            else: 
#                                print(res_js)
                    else:
                        print(str(time.time())+' - Receiving ... Work: '+self.work)
                        self.balance = mp.nstr(mp.fadd(mp.mpmathify(self.balance),1),64)[:-2]
                        async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
                            res = await session.post(f"http://{args.node_url}:{args.node_port}", json=blockcreate(account, config.representative, self.balance, self.hash, self.hash, self.work))
                            res_js = await res.json()
                            if 'hash' in res_js:
                                async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
                                    res = await session.post(f"http://{args.node_url}:{args.node_port}", json=process(res_js['block']))
                                    res_js = await res.json()
                                    if 'hash' in res_js:
                                        self.hash = res_js['hash']
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
#                                send = 1
#                            else: 
#                                print(res_js)
                except Exception as e: print(traceback.format_exc())
#                    print(res_js)
                print(str(time.time())+" - Hash: "+self.hash)
            else:
                print("Hash Not Confirmed")
            await asyncio.sleep(args.delay)

    async def analyse_votes(self):
        async with websockets.connect(f"ws://{args.node_url}:{args.socket_port}") as websocket:
            await websocket.send(json.dumps(subscription("confirmation", ack=True, options={"accounts":[
                account
            ]})))
            print(await websocket.recv())  # ack

            await websocket.send(json.dumps(subscription("vote", ack=True)))
            print(await websocket.recv())  # ack

            blocks = set()
            block_count = 0
            while 1:
                rec = json.loads(await websocket.recv())
                topic = rec.get("topic", None)
                if topic:
                    message = rec["message"]
                    if topic == "vote":
                        repaccount, vote_count = message["account"], len(message["blocks"])
                        votes[repaccount][vote_count-1] += 1
                        data = {}
                        data['time'] = rec['time']
                        data['account'] = message['account']
                        data['blocks'] = message['blocks']
                        self.vote_data.append(data)
                    elif topic == "confirmation":
                        data = {}
                        data['timestamp'] = self.timestamp
                        data['time'] = rec['time']
                        data['account'] = message['account']
                        data['hash'] = message['hash']
                        data['confirmation_type'] = message['confirmation_type']
                        self.conf_data.append(data)
                        self.hashes.append(message['hash'])
                        print("{} - {} blocks confirmed".format(str(time.time()), len(self.conf_data)))

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

analysis.writeBkup()
print('\nWriting to vote_hashes.json .....')
with open('vote_hashes.json', 'w') as jsonfile:
    jsonfile.write(json.dumps(analysis.conf_data))
print('\nWriting to vote_data.json .....')
with open('vote_data.json', 'w') as jsonfile:
    jsonfile.write(json.dumps(analysis.block_data))
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