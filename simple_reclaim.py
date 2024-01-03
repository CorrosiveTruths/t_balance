#!/usr/bin/env python3
import btrfs
import subprocess
import argparse
import sys
import statistics

parser = argparse.ArgumentParser(description='Targeted balance to free up unallocatable space')
parser.add_argument('path', help = '<path> to filesystem')
#parser.add_argument('-d', '--debug', help = 'debug mode', action='store_true')
args = parser.parse_args()

#chunks is a simple list of vaddrs with slices not in the most filled dev.
chunks = []
chunksizes = []
with btrfs.FileSystem(args.path) as fs:
    reclaimable = fs.usage().unallocatable_reclaimable
    if reclaimable == 0:
        print('Nothing to reclaim')
        #sys.exit()
    unalloc = []
    for device in fs.devices():
        unalloc.append((btrfs.fs_usage.DevUsage(device).unallocated, device.devid))
    devid = sorted(unalloc, reverse = True)[0][1] #Prohibit dev with most unallocated
    for chunk in fs.chunks():
        if chunk.type & btrfs.ctree.BLOCK_GROUP_TYPE_MASK == 1: #Only deal with DATA
            devs = set()
            chunksizes.append(chunk.length)
            for stripe in chunk.stripes:
                devs.add(stripe.devid)
            #print(chunk, devs)
            if devid not in devs:
                chunks.append(chunk.vaddr)
                #print('added')
    chunksize = statistics.mode(chunksizes)
    print('chunksize', btrfs.utils.pretty_size(chunksize))
    if reclaimable < chunksize:
        print('Nothing to reclaim')
        #sys.exit()
    print('Found', len(chunks), 'chunks not on dev', devid)
    while reclaimable >= chunksize:
        print('Unallocated reclaimable:', btrfs.utils.pretty_size(reclaimable))
        if chunks:
            vaddr_s = chunks.pop()
        else:
            sys.exit('No chunks left')
        print('Balancing chunk', vaddr_s)
        balance = ['btrfs', 'balance', 'start', '-dvrange='+str(vaddr_s)+'..'+str(vaddr_s+1), args.path]
        #print(balance)
        if subprocess.run(balance).returncode != 0:
            sys.exit('Balance Failed')
        reclaimable = fs.usage().unallocatable_reclaimable
print('Nothing to reclaim')
