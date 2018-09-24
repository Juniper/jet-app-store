#!/usr/bin/env python
#
# DO NOT ALTER OR REMOVE COPYRIGHT NOTICES OR THIS FILE HEADER
#
# Copyright (c) 2015 Juniper Networks, Inc.
# All rights reserved.
#
# Use is subject to license terms.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at http://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Copyright 2018 Juniper Networks Inc.

Sample Provisional Server code to perform GET request from the JET app.
This app should send the GET request in the following JSON format:

The response received by this client from JET app is of the following format:
|-------------------------------------------------------------------------------|
| 1byte version| 1 byte response status || 2 byte Payload length | 4 byte unused|
|<----------------------------------------------------------------------------->|
|                                 Payload Message                               |
|-------------------------------------------------------------------------------|

Payload will be of the format:
[{'ipv4address':'10.1.1.1', 'ipv6nh':'2001:2:1:1::1', 'community':'17676:10001' },..]
[{"action": "query", "prefix": "all"}]
Last message sent by this app will carry 0 payload length. In case, GET requests encounter any
error from the JUNOS router, then in that case, response status will be non-zero. This
should be a condition to exit the recv loop in the PS client.
"""

import time, sys, glob
import os
import pdb
import logging
from struct import *
import socket
import json
from struct import *
import re
JET_APP_VERSION = '1'


# create a socket object
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

host = 'IP of Router'
port = 8888
BUFFER_SIZE = 40960

# connection to hostname on the port opened by Server
s.connect((host, port))

# Sending route information in JSON format on the TCP socket
print("Creating Route Information JSON Object")
routeinfo = [{'prefix': 'all', 'action': 'query'}]
json_payload = json.dumps(routeinfo)
payload_length = len(json_payload)
request_header = pack('!ccll',JET_APP_VERSION,'1',payload_length,0)
data_with_header = request_header+json_payload
s.send(data_with_header)
print "Route Query Sent to the JET app: ", str(routeinfo)

flag = 1
count = 0

# Below while loop continuously waits on recv call. At first we read the header
# Based on the response status and payload length, we continue reading further.
# We also handle incomplete socket read by doing multiple reads till the payload
# length is complete.

while 1:
    try:
        data = s.recv(calcsize('!ccll'))
        if not data or len(data) < 8:
            print "Server closed connection, thread exiting."
            break
        version, resp_status, payload_length , reserved = unpack('!ccll', data)

        if (resp_status != '0' or payload_length == '0'):
            break
    except socket.error, (value, message):
        print 'socket.error - ' + message
        break

    try:
        body = ""
        tot_body = ""
        flag = 1
        while (flag == 1):
            body = s.recv(payload_length)
            tot_body += str(body)
            if not body:
                print "Nothing received for the body, thread exiting"
                break
            rcvd_body = len(body)
            if (rcvd_body < payload_length):
                payload_length -= rcvd_body
                continue
            else:
                flag = 0
                # To calculate the count of the messages received
                # Display the received route
                print tot_body
                count = count + len(re.findall('ipv4address', tot_body))
                data = ""
                payload_length = 0

    except socket.error, (value, message):
        print 'In receiving payload socket.error - ' + message
        break


print "Total routes received = ", count
print("Closing Socket")
s.close()


