#! /usr/bin/env python3

import requests
import json
import os
import argparse
from datetime import datetime
from hashlib import blake2b
from binascii import hexlify, unhexlify


def work_multiplier(difficulty: int):
    return float((1 << 64) - 0xffffffc000000000) / float((1 << 64) - difficulty)


def work_value(work: str, block_hash: str):
    reversed_work = bytearray(unhexlify(work))
    reversed_work.reverse()
    work_hash = bytearray(blake2b(
        b"".join([reversed_work, unhexlify(block_hash)]),
        digest_size=8).digest())
    work_hash.reverse()
    work_value = int(hexlify(work_hash), 16)
    return work_value


def get_batch(all_multipliers: dict, node: str, block_hashes: list):
    info = requests.post(node, json={
        "action":"blocks_info",
        "hashes": block_hashes,
        "include_not_found": True,
        "json_block": True}).json()

    if 'error' in info:
        raise Exception(info['error'])

    blocks = info['blocks']
    for h in block_hashes:
        contents = blocks[h]['contents']
        work, previous = contents['work'], contents['previous']
        # open block case
        if previous == "0000000000000000000000000000000000000000000000000000000000000000":
            get_key = requests.post(node, json={"action":"account_key", "account": blocks[h]['block_account']}).json()
            previous = get_key['key']
        all_multipliers[h] = work_multiplier(work_value(work, previous))

def main(node, file):

    try:
        os.rename('multipliers.json','multipliers.json.'+datetime.utcnow().strftime("%Y%m%d%H%M%S"))
        print('Renaming multipliers.json ...')
    except:
        print('multipliers.json does not exist, create new file ...')

    with open(file, 'r') as f:
        blocks = json.load(f)
    all_hashes = [d['hash'] for d in blocks]

    all_multipliers = dict()
    split = 100000
    chunks = [all_hashes[x:x+split] for x in range(0, len(all_hashes), split)]
    print("{} chunks of {}...".format(len(chunks), split))
    for i, hashes in enumerate(chunks):
        print(i+1, end='...', flush=True)
        get_batch(all_multipliers, node, hashes)
        print('done')

    with open('multipliers.json', 'w') as f:
        json.dump(all_multipliers, f)
    print("Saved to multipliers.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-host', '--node_url', type=str, help='Nano node url', default='localhost')
    parser.add_argument('-port', '--node_port', type=str, help='Nano node port', default='55000')
    parser.add_argument('file', type=str, help='confirmation_history.json file')
    args = parser.parse_args()
    node = "http://{}:{}".format(args.node_url, args.node_port)

    main(node, args.file)