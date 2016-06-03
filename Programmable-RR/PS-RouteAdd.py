import time, sys, glob
import os
import pdb
import socket
import json
from struct import *

JET_APP_VERSION = '1'

count = 0
prefix = 20
subnet = 32

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#s.settimeout( 100.0)
host = 'IP of RA'
port = 9999
s.connect((host, port))


for fnet in range(1,9):
    for snet in range(1,251):
        for tnet in range(1,251):
            DEST_PREFIX_ADD = str(prefix) + '.' + str(fnet) + '.' + str(snet) + '.' + str(tnet) + '/' + str(subnet)
            #print 'DEST_PREFIX_ADD',DEST_PREFIX_ADD
            count = count + 1
            routeinfo = [{ 'ipv4address':str(DEST_PREFIX_ADD), 'ipv6nh':'2001:1:1:1::2', 'community':'17676:10001', 'action':'add' }]
            print("Preparing Route Information JSON Object")
            print("\n")
            print routeinfo
            
            json_payload = json.dumps(routeinfo)
            payload_length = len(json_payload)
            request_header = pack('!ccll',JET_APP_VERSION,'1',payload_length,0)
            data_with_header = request_header+json_payload
            sent_bytes = s.send(data_with_header)
            print "Route Information Sent on socket, total bytes = ",  sent_bytes
            print("\n")
            info1 = s.recv(1024)
            print(info1)

print("Closing Socket")
s.close()

print 'Total Added Routes',count
print("\n")
