#!/usr/bin/env python3
import argparse
import requests
import json
import config

parser = argparse.ArgumentParser()
parser.add_argument('-host', '--node_url', type=str, help='Nano node url', default='localhost')
parser.add_argument('-port', '--node_port', type=str, help='Nano node port', default='55000')
parser.add_argument('-save', '--save', type=int, help='Save blocks to disk how often (in seconds) should be multiple of --delay', default=180)
parser.add_argument('-delay', '--delay', type=int, help='recorder delay (in seconds)', default=15)
parser.add_argument('-timeout', '--timeout', type=float, help='rpc request timeout (in seconds)', default=60)
parser.add_argument('-file', '--file', type=str, help='Filename to upload', default='')
args = parser.parse_args()

def upload(file):
    data = {"source":config.upload_user,"key":config.upload_key} 

    url = 'https://nano-faucet.org/beta/chart/upload/'

    with open(file, 'rb') as payload:
        files = {'file': (file, payload)}
        r = requests.post(url=url, data=data, files=files)
    #print(r.status_code)
    print(r.text)

if args.file != '':
    upload(args.file)
else:
    print('Please provide a filename with -file')