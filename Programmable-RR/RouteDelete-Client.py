"""
Copyright 2018 Juniper Networks Inc.

This file defines the Route delete API call.
"""

import time, sys, glob
import os
import pdb
import socket
import json
import time
from struct import *

JET_APP_VERSION = '1'
routeinfo = []

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host = 'IP of Router'

port = 8888
s.connect((host, port))


DEST_PREFIX_ADD = '192.168.10.1/32'
routeinfo.append({'ipv4address':str(DEST_PREFIX_ADD), 'action':'delete' })

print("Preparing Route Information JSON Object")
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
