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
#

"""
Sample application to handle the requests for setting and getting of BGP routes using
JET infra on JUNOS devices. This app acts as a server/forwarder for requests from a
Provisional Server (PS) client.This app can handle at most two concurrent requests so that
this app can be used on-box on low-end JUNOS routers and it cannot be two concurrent GET requests.
This app listens to requests from PS for BGP route add, modify, delete and
get requests. The requests have to be provided by the PS in JSON format.

In case of GET requests, this app will respond to the PS in the following message format:
|-------------------------------------------------------------------------------|
| 1byte version| 1 byte response status || 2 byte Payload length | 4 byte unused|
|<----------------------------------------------------------------------------->|
|                                 Payload Message                               |
|-------------------------------------------------------------------------------|

Last message sent by this app will carry 0 payload length. In case, GET requests encounter any
error from the JUNOS router, then in that case, response status will be non-zero. This
should be a condition to exit the recv loop in the PS client.
"""

import socket, select
import os
from struct import *
from jnpr.jet.JetHandler import *
import sys, traceback

from thrift import Thrift
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

from Queue import Queue
from threading import Thread
import threading
import signal
import time

# Variables for THRIFT/MQTT connection
HOST = 'IP of RA'

PORT = 9090
CLIENT_ID = "102"
USER = 'lab'
PASSWORD = 'lab'
TIMEOUT = 5
JET_APP_VERSION = '1'
HEADER_LENGTH = calcsize('!ccll')


requestQ = Queue()

# Message queue for response to be sent to PS
responseQ = Queue()
clrgetsock = 0
total_sent_msg = 0
getwaitflag = 0
#RECV_BUFFER = 4096 # Max read buffer size
RECV_BUFFER = 10000
#CONNECTION_LIST = []
calling_thread_event = threading.Event()

# This function is executed by the dispatch thread
# It picks all the responses from the dispatch Queue and
# processes those messages along with the last message
def sendtoPS():
    global calling_thread_event
    global clrgetsock
    global total_sent_msg
    global getwaitflag
    while True:
        if not responseQ.empty() and getwaitflag != 1:
            rspMsg = responseQ.get()
            responseQ.task_done()
            # Verify if the entry in the Q is the end of the messages
            # if not then process it
            if (rspMsg == 'END_OF_DATA'):
                eod_data = pack('!ccll',JET_APP_VERSION,'1',0,0)
                getwaitflag = 1
                try:
                    clrgetsock.sendall(str(eod_data))
                    #responseQ.queue.clear()
                except socket.error, (value, message):
                    getwaitflag = 1
                    print 'socket.error in sending eod - ' + message
		    #os.kill(calling_thread_id, signal.SIGUSR1)
		    calling_thread_event.set()
                    #break
            else:
                str_res = RoutingBgpRouteGetReply()
                tbuf = TTransport.TMemoryBuffer(rspMsg)
                tmem_protocol = TBinaryProtocol.TBinaryProtocol(tbuf)
                str_res.read(tmem_protocol)
                if (str_res.status == 0):
                    bgpRouteEntry = str_res.bgp_routes
                    json_data = "["
                    for route in bgpRouteEntry:
                        print route
                        json_data += "{'ipv4address':'" + str(route.dest_prefix.RoutePrefixAf.inet.AddrFormat.addr_string) + "', 'ipv6nh':'" + str(
                            route.protocol_nexthops[0].AddrFormat.addr_string) + "', 'community':'" + route.communities.com_list[0].community_string + "' },"

                    json_data = json_data[:-1]
                    json_data += "]"
                    data = pack('!ccll',JET_APP_VERSION,str(str_res.status), len(str(json_data)),0)
                    data += str(json_data)
                    json_data = ""
                    try:
                        clrgetsock.sendall(str(data))
                    except socket.error, (value, message):
                        print 'socket.error in sending data  - ' + message
                        getwaitflag = 1
		        #os.kill(calling_thread_id, signal.SIGUSR1)
                        calling_thread_event.set()
                        #break
                else:
                    data = pack('!ccll', JET_APP_VERSION, str(str_res.status), 0, 0)
                    try:
                        clrgetsock.sendall(str(data))
                        getwaitflag = 1
                        #break
                    except socket.error, (value, message):
                        print 'socket.error - ' + message
                        getwaitflag = 1
                        #os.kill(calling_thread_id, signal.SIGUSR1)
			calling_thread_event.set()
                        #break
                total_sent_msg += 1
        else:
             if getwaitflag == 1:
                eod_data = pack('!ccll',JET_APP_VERSION,'1', 0,0)
                try:
                    clrgetsock.sendall(str(eod_data))
                except socket.error, (value, message):
                    print 'socket.error in sending eod - ' + message
		finally:
		    calling_thread_event.set()
		    #break

def destRoute(destPrefix, family):
    addrForm = IpAddressAddrFormat(destPrefix)
    jnxP = JnxBaseIpAddress(addrForm)
    dstP = RoutePrefixRoutePrefixAf()
    if family is 'inet':
        dstP.inet = jnxP
    elif family is 'inet6':
        dstP.inet6 = jnxP
    elif family is 'inetvpn':
        dstP.inetvpn = jnxP
    elif family is 'inet6vpn':
        dstP.inet6vpn = jnxP
    destPfx = RoutingRoutePrefix(dstP)
    return destPfx


def destTableName(destTable):
    tableName = RoutingRouteTableName(destTable)
    tableFormat = RouteTableRtTableFormat()
    tableFormat.rtt_name = tableName
    routeTable = RoutingRouteTable(tableFormat)
    return routeTable


def destTableId(table):
    tableName = RoutingRouteTableName(table)
    routeTab = RoutingRtTblIdRequest(tableName)
    routeTableId = prpd.RouteTableIdGet(routeTab)
    tableFormat = RouteTableRtTableFormat()
    tableFormat.rtt_id = routeTableId.rt_tbl_id
    routeTable = RoutingRouteTable(tableFormat)
    return routeTable


def destProtocol(proto):
    print 'Protocol:', proto
    rpdReq = RoutingRtProtoRegRequest(proto)
    protoReg = prpd.RouteProtoRegister(rpdReq)
    if protoReg.ret_code == 0:
        print 'Proto Name', protoReg.proto
        print 'Proto handle', protoReg.handle
        return protoReg.proto
    else:
        return 0


def ip_to_uint32(ip):
    t = socket.inet_aton(ip)
    print struct.unpack("I", t)[0]
    return struct.unpack("I", t)[0]


def uint32_to_ip(ipn):
    t = struct.pack("I", ipn)
    return socket.inet_ntoa(t)


# Function to handle routeget message
# This callback simply puts all the received messages in a dispatch Queue
# This allows it to capture all the notifications successfully
def handleMessage(message):
    global eod
    if len(message) == 0:
        print "END OF DATA"
        eod = 1
        responseQ.put("END_OF_DATA")
    elif eod == 1:
        eod = 0
    else:
        responseQ.put(str(message))


def AppRouteAdd(clientsocket, routereq):

    try:
        # Intialising BGP
        strBgpReq = RoutingBgpRouteInitializeRequest()
        result = bgp.BgpRouteInitialize(strBgpReq)
        print 'Invoked BgpRouteInitialize API inside AppRouteAdd.. \nreturn = ', result.status

        #Determine the no of routes in request
        #lenjson = len(routereq)
        #print lenjson

        # List for route entries to be passed to API
        routeindex = 0
        routeList = list()

        for jsonentry in routereq:

            # Fetching route info from json request
            destroute = jsonentry['ipv4address']
            destroutelst = destroute.split('/')
            DEST_PREFIX_ADD = destroutelst[0]
            DEST_PREFIX_LEN = destroutelst[1]
            DEST6_NEXT_HOP = jsonentry['ipv6nh']
            AddCommunity = jsonentry['community']
            DEST_ROUTE_TABLE = 'inet.0'
            print "Route add request received for route:", str(destroute)

            # Preparing parameters to call BGP Route Add API
            nhJnxP = IpAddressAddrFormat(DEST6_NEXT_HOP)
            nextHop = JnxBaseIpAddress(nhJnxP)
            routeParams = RoutingBgpRouteEntry()
            routeParams.dest_prefix = destRoute(DEST_PREFIX_ADD, "inet")
            routeParams.dest_prefix_len = DEST_PREFIX_LEN
            routeParams.table = destTableName(DEST_ROUTE_TABLE)
            routeParams.protocol_nexthops = [nextHop]
            routeParams.path_cookie = '10'
            routeParams.protocol = 2
            comm = RoutingCommunity(AddCommunity)
            bgpAttrCommunity = RoutingCommunityList([comm])
            routeParams.communities = bgpAttrCommunity
            routeindex = routeindex + 1
            routeList.append(routeParams)

        #print 'Fetched routes from JSON.. \nreturn = ',
        #print 'Total Routes.. =', routeindex

       # Calling BGP Route Add API to program routes
        updReq = RoutingBgpRouteUpdateRequest(routeList)
        # print updReq
        addRes = bgp.BgpRouteAdd(updReq)
        print 'Invoked Route Add API Status\nreturn = ', addRes
        print 'Invoked Route Add API Status\nreturn = ', addRes.status

        # API reply captured
        statusval = addRes.status
        print('addRes.status =', statusval)

        print "Sending reply to PS"
        rtaddjsonreply = [{'returncode': str(statusval)}]
        try:
            clientsocket.send(json.dumps(rtaddjsonreply))
        except:
            print("SocketIO: Write failed.. \n")

    except:
        print "Sending reply to PS"
        # Return code where there are issues executing Add APIs
        rtaddjsonreply = [{'returncode': '101'}]
        try:
            clientsocket.send(json.dumps(rtaddjsonreply))
        except:
            print("SocketIO: Write failed.. \n")

    return


def AppRouteModify(clrmodsock, routereq):

    try:
        # Intialising BGP
        strBgpReq = RoutingBgpRouteInitializeRequest()
        result = bgp.BgpRouteInitialize(strBgpReq)
        print 'Invoked BgpRouteInitialize API \nreturn = ', result.status

        # List for route entries to be passed to API
        routeindex = 0
        routeList = list()


        for jsonentry in routereq:

            # Fetching route info from json request
            destroute = jsonentry['ipv4address']
            destroutelst = destroute.split('/')
            DEST_PREFIX_ADD = destroutelst[0]
            DEST_PREFIX_LEN = destroutelst[1]
            DEST6_NEXT_HOP = jsonentry['ipv6nh']
            ModCommunity = jsonentry['community']
            print "Route Modify request received for route:", str(destroute)

            # Preparing parameters to call BGP Update API
            DEST_ROUTE_TABLE = 'inet.0'
            nhJnxP = IpAddressAddrFormat(DEST6_NEXT_HOP)
            nextHop = JnxBaseIpAddress(nhJnxP)
            routeParams = RoutingBgpRouteEntry()
            routeParams.dest_prefix = destRoute(DEST_PREFIX_ADD, "inet")
            routeParams.dest_prefix_len = DEST_PREFIX_LEN
            routeParams.table = destTableName(DEST_ROUTE_TABLE)
            routeParams.protocol_nexthops = [nextHop]
            routeParams.path_cookie = '10'
            routeParams.protocol = 2
            comm = RoutingCommunity(ModCommunity)
            bgpAttrCommunity = RoutingCommunityList([comm])
            routeParams.communities = bgpAttrCommunity
            routeindex = routeindex + 1
            routeList.append(routeParams)

        print 'Fetched routes from JSON..'
        print 'Total Routes.. =', routeindex

        #updReq = RoutingBgpRouteUpdateRequest([routeParams])
        updReq = RoutingBgpRouteUpdateRequest(routeList)
        # print updReq
        addRes = bgp.BgpRouteUpdate(updReq)
        print 'Invoked Route Add API Status\nreturn = ', addRes
        print 'Invoked Route Add API Status\nreturn = ', addRes.status

        # API reply captured
        statusval = addRes.status
        addoppcomp = addRes.operations_completed
        print('addRes.status =', statusval)
        print('addoppcomp =', addoppcomp)

        print "Sending info to PS"
        rtmodjsonreply = [{'returncode': str(statusval)}]
        try:
            clrmodsock.send(json.dumps(rtmodjsonreply))
        except:
            print("SocketIO: Write failed.. \n")

    except:
        print "Sending reply to PS"
        # Return code where there are issues executing Update APIs
        rtmodjsonreply = [{'returncode': '104'}]
        try:
            clrmodsock.send(json.dumps(rtmodjsonreply))
        except:
            print("SocketIO: Write failed.. \n")

    return


def AppRouteDelete(clrdelsock, routereq):

    try:
        # Intialising BGP
        strBgpReq = RoutingBgpRouteInitializeRequest()
        result = bgp.BgpRouteInitialize(strBgpReq)
        print 'Invoked BgpRouteInitialize API \nreturn = ', result.status

        # List for route entries to be passed to API
        routeindex = 0
        routeList = list()

        for jsonentry in routereq:
            # Fetching route info from json request
            destroute = jsonentry['ipv4address']
            destroutelst = destroute.split('/')
            DEST_PREFIX_ADD = destroutelst[0]
            DEST_PREFIX_LEN = destroutelst[1]
            DEST6_NEXT_HOP = jsonentry['ipv6nh']
            DEST_ROUTE_TABLE = 'inet.0'
            print "Route remove request received for route:", str(destroute)

            # Preparing parameters to call BGP Route Remove API
            tableName = RoutingRouteTableName(DEST_ROUTE_TABLE)
            tableFormat = RouteTableRtTableFormat()
            tableFormat.rtt_name = tableName
            routeTable = RoutingRouteTable(tableFormat)
            addrForm = IpAddressAddrFormat(str(DEST_PREFIX_ADD))
            jnxP = JnxBaseIpAddress(addrForm)
            dstP = RoutePrefixRoutePrefixAf()
            dstP.inet = jnxP
            destPrefix = RoutingRoutePrefix(dstP)
            routeParams = RoutingBgpRouteEntry()
            routeParams.dest_prefix = destPrefix
            routeParams.dest_prefix_len = DEST_PREFIX_LEN
            routeParams.table = routeTable
            routeParams.path_cookie = '10'
            routeindex = routeindex + 1
            routeList.append(routeParams)

        remReq = RoutingBgpRouteRemoveRequest(0, routeList)
        remRes = bgp.BgpRouteRemove(remReq)
        # print remReq
        print 'Invoked Route remove API Status\nreturn = ', remRes
        print 'Invoked Route remove API Status\nreturn = ', remRes.status

        # API reply captured
        delstatus = remRes.status
        print "Sending info to PS"
        print('remRes.status =', delstatus)

        print "Sending reply to PS"
        rtaddjsonreply = [{'returncode': str(delstatus)}]
        try:
            clrdelsock.send(json.dumps(rtaddjsonreply))
        except:
            print("SocketIO: Write failed.. \n")

    except:
        # Condition to handle when API execution was not successful
        rtdeljsonreply = [{'returncode': '103'}]
        try:
            clrdelsock.send(json.dumps(rtdeljsonreply))
        except:
            print("SocketIO: Write failed.. \n")


    return


def AppRouteGet(clrgetsock, routereq, evHandle):

    # Flag to indicate that the disptach thread execution is complete
    global getwaitflag
    global calling_thread_event
    getwaitflag = 0
    # Intialising BGP
    strBgpReq = RoutingBgpRouteInitializeRequest()
    try:
        result = bgp.BgpRouteInitialize(strBgpReq)
        print 'Invoked BgpRouteInitialize API \nreturn = ', result.status
    except Exception as tx:
        print 'Received exception: %s' % (tx.message)
        eod_data = pack('!ccll',JET_APP_VERSION,'1',0,0)
        clrgetsock.sendall(eod_data)
        os._exit(1)

    # Topic to MQTT to stream the BGP routes
    topic = "bgp/DoubleUnaryStreamBgpRouteGet"

    stream = evHandle.CreateStreamTopic(topic)
    evHandle.Subscribe(stream, handleMessage, 2)

    DEST_ROUTE_TABLE = 'inet.0'
    addrForm = IpAddressAddrFormat('0.0.0.0')
    jnxP = JnxBaseIpAddress(addrForm)
    dstP = RoutePrefixRoutePrefixAf()
    dstP.inet = jnxP
    destPrefix = RoutingRoutePrefix(dstP)
    tableName = RoutingRouteTableName(DEST_ROUTE_TABLE)
    tableFormat = RouteTableRtTableFormat()
    tableFormat.rtt_name = tableName
    routeTable = RoutingRouteTable(tableFormat)
    routeParams = RoutingBgpRouteEntry()
    routeParams.dest_prefix = destPrefix
    routeParams.dest_prefix_len = '0'
    routeParams.table = routeTable
    bgpRouteReq = RoutingBgpRouteGetRequest()
    bgpRouteReq.bgp_route = routeParams
    bgpRouteReq.or_longer = True
    bgpRouteReq.route_count = '250'
    bgpRouteReq.active_only = False
    try:
        routeGetReply = bgp.BgpRouteGet(bgpRouteReq, topic)
    except Exception as e:
        print 'Received exception in calling JET api %s' %(e.message)
        eod_data = pack('!ccll',JET_APP_VERSION,'1',0,0)
        clrgetsock.sendall(eod_data)
        os._exit(1)
    # Start the dispatcher thread
    #dispatch_thread = Thread(target=sendtoPS, args=(clrgetsock,), name = str(clrgetsock))
    #dispatch_thread.setDaemon(False)
    responseQ.queue.clear()
    #dispatch_thread.start()

    #dispatch_thread.join()
    calling_thread_event.wait()
    calling_thread_event.clear()
    print 'Invoked RouteGet API\nreturn = ', routeGetReply
    #if getwaitflag != 1:
    getwaitflag = 0 
    #responseQ.queue.clear()
    if not responseQ.empty():
        responseQ.queue.clear()
    return



def allRouteApis():
    while True:
        routereq, clientsocket = requestQ.get()
        try:
            if(routereq[0]['action'] == 'add'):
                thvalue = AppRouteAdd(clientsocket, routereq)

            elif(routereq[0]['action'] == 'query'):
                global clrgetsock
                clrgetsock = clientsocket
                thvalue = AppRouteGet(clrgetsock, routereq, evHandle)

            elif(routereq[0]['action'] == 'delete'):
                global clrdelsock
                clrdelsock = clientsocket
                thvalue = AppRouteDelete(clrdelsock, routereq)

            elif(routereq[0]['action'] == 'modify'):
                global clrmodsock
                clrmodsock = clientsocket
                thvalue = AppRouteModify(clrmodsock, routereq)

            else:
                print("Unknown request could not be processed")
                print ("Sending reply to PS")
                jsonreply = [{'returncode': '100'}]
                try:
                    clientsocket.send(json.dumps(jsonreply))
                except:
                    print("SocketIO: Write failed.. \n")

        except Exception as e:
                print("Failed to process the request")
		print e.message
		# traceback.print_last()
		traceback.print_stack()
                print ("Sending failure reply to PS")
                jsonreply = [{'returncode': '100'}]
                try:
                    clientsocket.send(json.dumps(jsonreply))
                except:
                    print("SocketIO: Write failed.. \n")
        requestQ.task_done()


try:
    CONNECTION_LIST = []
    for i in range(1):
        t = Thread(target=allRouteApis)
        t.setDaemon(True)
        t.start()
    dispatch_thread = Thread(target=sendtoPS)
    dispatch_thread.setDaemon(True)
    dispatch_thread.start()
    # Connection to JSD
    client = JetHandler()

    # Open a Request Response session
    client.OpenRequestResponseSession(
        device=HOST,
        port=PORT,
        user=USER,
        password=PASSWORD,
        ca_certs=None,
        client_id=CLIENT_ID)
    print "Connected to the client"

    # Open a notification channel to receive the streaming GET response from JSD
    evHandle = client.OpenNotificationSession(
        HOST,
        1883,
        None,
        None,
        None,
        DEFAULT_MQTT_TIMEOUT,
        "",
        True)
    bgp = client.GetRoutingBgpRoute()
    prpd = client.GetRoutingBase()

    purgeTime = 30
    # Variables for RouteGet Operation
    eod = 0
    count = 0
    getroutelist = []
    getwaitflag = 0
    
    # Dictionary of sockets waiting on incomplete data for requests
    sockdict = {}
    
    # Route request queue
    routereqDict = {}

    # Socket creation to get the PS requests
    serversocket = socket.socket(
        socket.AF_INET, socket.SOCK_STREAM)

    port = 9999
    serversocket.bind(('', port))

    print("Listening to Incoming Connections from the Provisioning Server")
    serversocket.listen(2)
    CONNECTION_LIST.append(serversocket)

    # Variable for capturing thread return
    thvalue = 0
    while True:
        # Establish a incoming connection from Client
        read_sockets,write_sockets,error_sockets = select.select(CONNECTION_LIST,[],[])
        for sock in read_sockets:
            if sock == serversocket:
                sockfd, addr = serversocket.accept()
                CONNECTION_LIST.append(sockfd)
                print "Client (%s, %s) connected" % addr
                print "Client socket fd = ", sock
            else:
                try:
                    # always try to read only the header first if socket not in the dict
                    if sock in sockdict:
                        print sock, 'already present in the dictionary, will read bytes =', sockdict[sock]
                    # check for the remaining data to be read
                        psreq = sock.recv(sockdict[sockfd])
                        readlen = len(psreq)
                        print sock, 'reading ', readlen, ' bytes'
                        if readlen < sockdict[sock]:
                            # need to read again
                            sockdict[sock] -= readlen
                            routereqDict[sock] += psreq
                            print 'Read incomplete yet'
                        else:
                            # complete read done
                            print 'Read completed'
                            routereqDict[sock] += psreq
                            routereq = (json.loads(routereqDict[sock]))
                            requestQ.put((routereq, sock))
                            sockdict.pop(sock)
                            routereqDict.pop(sock)
                    else:
                                        
                        psreq = sock.recv(HEADER_LENGTH)
                        if not psreq:
                            sock.close()
                            CONNECTION_LIST.remove(sock)
                        else:
                            
                            # add this request to the sockdict
                            Version, req_type, payload_length , reserved = unpack('!ccll', psreq)
                            print 'New Request received of size: ', payload_length
                            sockdict[sock] = payload_length
                            routereqDict[sock] = ''
                            #routereq = (json.loads(psreq))
                            #requestQ.put((routereq, sock))
                except Exception as e:
		    print 'Exception:', e.message
                    sock.close()
                    CONNECTION_LIST.remove(sock)
                    continue
    serversocket.close()
    requestQ.join()

    # Close session
    evHandle.Unsubscribe()
    print "Closing the Client"
    client.CloseRequestResponseSession()
    client.CloseNotificationSession()


except Thrift.TException as tx:
    print(('%s' % (tx.message)))

