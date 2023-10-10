#!/usr/bin/env python3
import btrfs
import subprocess
import argparse
import sys

parser = argparse.ArgumentParser(description='Targeted balance to free up chunks that are unallocatable because of unbalanced allocations.')
parser.add_argument('path', help = '<path> to raid1 filesystem')
parser.add_argument('-d', '--debug', help = 'debug mode', action='store_true')
args = parser.parse_args()

#chunks is a simple list vaddrs with slices not in the most filled dev.
chunks = []
with btrfs.FileSystem(args.path) as fs:
    unalloc = []
    for device in fs.devices():
        unalloc.append((btrfs.fs_usage.DevUsage(device).unallocated, device.devid))
    devid = sorted(unalloc, reverse = True)[0][1] #Prohibit dev with most unallocated
    for chunk in fs.chunks():
        if (chunk.type == 17 and #Only deal with DATA/RAID1
                chunk.stripes[0].devid != devid and
                chunk.stripes[1].devid != devid):
            chunks.append(chunk.vaddr)
    print('Found', len(chunks), 'chunks not on dev', devid)
    reclaimable = fs.usage().unallocatable_reclaimable
    while reclaimable > 0:
        print('Unallocated reclaimable:', btrfs.utils.pretty_size(reclaimable))
        vaddr_s = chunks.pop()
        print('Balancing chunk', vaddr_s)
        balance = ['btrfs', 'balance', 'start', '-dvrange='+str(vaddr_s)+'..'+str(vaddr_s+1), args.path]
        #print(balance)
        if subprocess.run(balance).returncode != 0:
            sys.exit('Balance Failed')
        reclaimable = fs.usage().unallocatable_reclaimable
print('Nothing to reclaim')
