#!/usr/bin/env python3
import btrfs
import subprocess
import argparse
import sys
import random
from itertools import combinations

parser = argparse.ArgumentParser(description='Targeted balance to free up chunks that are unallocatable because of unbalanced allocations.')
parser.add_argument('path', help = '<path> to raid1 filesystem')
parser.add_argument('-d', '--debug', help = 'debug mode', action='store_true')
args = parser.parse_args()

#chunks is a dictionary w/ stripe tuple as key and a list of randomised vaddrs.
chunks = {}
with btrfs.FileSystem(args.path) as fs:
    devices = []
    for device in fs.devices():
        devices.append(device.devid)
    for comb in combinations(devices, 2):
        chunks[(tuple(set(comb)))] = [] #set faster than sorted?
    for chunk in fs.chunks():
        if chunk.type == 17: #Only deal with DATA/RAID1
            chunk_pair = tuple(set([chunk.stripes[0].devid, chunk.stripes[1].devid]))
            chunks[chunk_pair].append(chunk.vaddr)
    print('Chunk pairs')
    for key in sorted(chunks.keys()):
        print(str(key)+':', len(chunks[key]))
        random.shuffle(chunks[key])
    reclaimable = fs.usage().unallocatable_reclaimable
    while reclaimable > 0: #Could check for unalloc even-ness for general alt bal?
        print('Unallocated reclaimable:', btrfs.utils.pretty_size(reclaimable))
        unalloc = []
        for device in fs.devices():
            unalloc.append((btrfs.fs_usage.DevUsage(device).unallocated, device.devid))
        #print(sorted(unalloc))
        devs_by_unalloc = []
        for ddid in sorted(unalloc)[:-1]:
            devs_by_unalloc.append(ddid[1])
        pair_order = []
        for comb in combinations(devs_by_unalloc, 2):
            pair_order.append(tuple(sorted(comb)))
        #print(pair_order)
        print('Balancing pair:')
        vaddr_s = ''
        for pair in pair_order:
            if len(chunks[pair]) > 0:
                vaddr_s = chunks[pair].pop()
                print(pair, len(chunks[pair]))
                break
        if vaddr_s == '':
            sys.exit('No chunk found')
        balance = ['btrfs', 'balance', 'start', '-dvrange='+str(vaddr_s)+'..'+str(vaddr_s+1), args.path]
        #print(balance)
        if subprocess.run(balance).returncode != 0:
            sys.exit('Balance Failed')
        reclaimable = fs.usage().unallocatable_reclaimable
print('Nothing to reclaim')
