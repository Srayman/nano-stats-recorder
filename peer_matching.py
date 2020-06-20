#!/usr/bin/env python3

import requests
import json
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--node', type=str, default='[::1]:7076')
args = parser.parse_args()


def node(data):
    return requests.post('http://'+args.node, json=data).json()

get_peers = node({"action":"peers", "peer_details":"true"})
telemetry = node({"action":"node_telemetry", "raw":"true"})

all_peers = get_peers["peers"]

other_peers = {k: v["protocol_version"] for k,v in all_peers.items() if v["protocol_version"] != '18'}
peers = {k: v["protocol_version"] for k,v in all_peers.items() if v["protocol_version"] == '18'}

match = []
unmatch = []

for peer in telemetry["metrics"]:
    ip = '['+peer["address"]+']:'+peer["port"]
    if ip in peers:
        network = peers.pop(ip)
        match.append(ip)
    else:
        unmatch.append(ip)

print("{} Match\n{}\n\n\n{} Unmatch\n{}\n\n".format(len(match), match, len(unmatch), unmatch))

print("{} Unknown\n{}".format(len(peers), peers))
