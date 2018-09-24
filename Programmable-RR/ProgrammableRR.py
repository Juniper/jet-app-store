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
Copyright 2018 Juniper Networks Inc.
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
from struct import *
from jnpr.jet.JetHandler import *
import logging
from logging.handlers import RotatingFileHandler
import time
from thrift import Thrift
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

from Queue import Queue
from threading import Thread
import threading

# Logging Parameters
DEFAULT_LOG_FILE_NAME = '/tmp/jetapp.log'
#DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_LEVEL = logging.CRITICAL

# Enable Logging to a file
FORMAT = "[%(filename)s:%(lineno)s - %(funcName)s ] %(message)s"
logging.basicConfig(filename=DEFAULT_LOG_FILE_NAME, level=DEFAULT_LOG_LEVEL, format = FORMAT)
handler = RotatingFileHandler(DEFAULT_LOG_FILE_NAME,maxBytes=1024)
LOG = logging.getLogger(__name__)
LOG.addHandler(handler)

# Variables for THRIFT/MQTT connection
HOST = 'IP of Router'
PORT = 9090
CLIENT_ID = "100"
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
            rspMsg = responseQ.get()
            responseQ.task_done()
            # Verify if the entry in the Q is the end of the messages
            # if not then process it
            if (rspMsg == 'END_OF_DATA'):
                eod_data = pack('!ccll',JET_APP_VERSION,'1',0,0)
                try:
                    clrgetsock.sendall(str(eod_data))
		    calling_thread_event.set()
                except socket.error, (value, message):
                    getwaitflag = 1
                    LOG.debug('socket.error in sending eod - %s' %str(message))
                    calling_thread_event.set()
            else:
                str_res = RoutingBgpRouteGetReply()
                tbuf = TTransport.TMemoryBuffer(rspMsg)
                tmem_protocol = TBinaryProtocol.TBinaryProtocol(tbuf)
                str_res.read(tmem_protocol)
                if (str_res.status == 0):
                    bgpRouteEntry = str_res.bgp_routes
                    json_data = "["
                    for route in bgpRouteEntry:
                        #print route
                        json_data += "{'ipv4address':'" + str(route.dest_prefix.RoutePrefixAf.inet.AddrFormat.addr_string) + "', 'next_hop':'" + str(
                            route.protocol_nexthops[0].AddrFormat.addr_string) + "', 'community':'" + route.communities.com_list[0].community_string + "' },"

                    json_data = json_data[:-1]
                    json_data += "]"
                    data = pack('!ccll',JET_APP_VERSION,str(str_res.status), len(str(json_data)),0)
                    data += str(json_data)
                    json_data = ""
                    try:
                        clrgetsock.sendall(str(data))
                    except socket.error, (value, message):
                        LOG.debug('socket.error in sending eod - %s' %str(message))
                        getwaitflag = 1
                        calling_thread_event.set()
                else:
                    data = pack('!ccll', JET_APP_VERSION, str(str_res.status), 0, 0)
                    try:
                        clrgetsock.sendall(str(data))
			calling_thread_event.set()
                        getwaitflag = 1
                    except socket.error, (value, message):
                        LOG.debug('socket.error in sending eod - %s' %str(message))
                        getwaitflag = 1
                        calling_thread_event.set()
                total_sent_msg += 1

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
    LOG.info('Protocol: %s' %str(proto))
    rpdReq = RoutingRtProtoRegRequest(proto)
    protoReg = prpd.RouteProtoRegister(rpdReq)
    if protoReg.ret_code == 0:
        LOG.info('Proto Name: %s, Proto handle:%s' %(str(protoReg.proto), str(protoReg.handle)))
        return protoReg.proto
    else:
        return 0


def ip_to_uint32(ip):
    t = socket.inet_aton(ip)
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
        LOG.info("END OF DATA")
        eod = 1
        responseQ.put("END_OF_DATA")
    elif eod == 1:
        eod = 0
    else:
        responseQ.put(str(message))
        time.sleep(2)


def AppRouteAdd(clientsocket, routereq):

    try:
        # Intialising BGP
        strBgpReq = RoutingBgpRouteInitializeRequest()
        result = bgp.BgpRouteInitialize(strBgpReq)
        LOG.info('Invoked BgpRouteInitialize API inside AppRouteAdd.. \nreturn = %s ' %str(result.status))
        # List for route entries to be passed to API
        routeindex = 0
        routeList = list()

        for jsonentry in routereq:

            # Fetching route info from json request
            destroute = jsonentry['ipv4address']
            destroutelst = destroute.split('/')
            DEST_PREFIX_ADD = destroutelst[0]
            DEST_PREFIX_LEN = destroutelst[1]
            DEST6_NEXT_HOP = jsonentry['next_hop']
            AddCommunity = jsonentry['community']
            DEST_ROUTE_TABLE = 'inet.0'
            LOG.info("Route add request received for route:%s" %str(destroute))

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
            #routeParams.route_oper_flag = "4"
            comm = RoutingCommunity(AddCommunity)
            bgpAttrCommunity = RoutingCommunityList([comm])
            routeParams.communities = bgpAttrCommunity
            routeindex = routeindex + 1
            routeList.append(routeParams)

       # Calling BGP Route Add API to program routes
        updReq = RoutingBgpRouteUpdateRequest(routeList)
        addRes = bgp.BgpRouteAdd(updReq)
        LOG.info('Invoked Route Add API Status\nreturn = %s' %str(addRes))

        # API reply captured
        statusval = addRes.status
        route_op_count = addRes.operations_completed

        LOG.info("Sending reply to PS")
        rtaddjsonreply = [{'returncode': str(statusval)}]
        try:
            clientsocket.send(json.dumps(rtaddjsonreply))
        except:
            LOG.debug("SocketIO: Write failed")

    except:
        LOG.info("Sending reply to PS")
        # Return code where there are issues executing Add APIs
        rtaddjsonreply = [{'returncode': '101'}]
        try:
            clientsocket.send(json.dumps(rtaddjsonreply))
        except:
            LOG.debug("SocketIO: Write failed")

    return


def AppRouteModify(clrmodsock, routereq):

    try:
        # Intialising BGP
        strBgpReq = RoutingBgpRouteInitializeRequest()
        result = bgp.BgpRouteInitialize(strBgpReq)
        LOG.info('Invoked BgpRouteInitialize API \nreturn = %s' %str(result.status))

        # List for route entries to be passed to API
        routeindex = 0
        routeList = list()

        for jsonentry in routereq:

            # Fetching route info from json request
            destroute = jsonentry['ipv4address']
            destroutelst = destroute.split('/')
            DEST_PREFIX_ADD = destroutelst[0]
            DEST_PREFIX_LEN = destroutelst[1]
            DEST6_NEXT_HOP = jsonentry['next_hop']
            ModCommunity = jsonentry['community']
            LOG.info("Route Modify request received for route: %s" %str(destroute))

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
            #routeParams.route_oper_flag = "4"
            comm = RoutingCommunity(ModCommunity)
            bgpAttrCommunity = RoutingCommunityList([comm])
            routeParams.communities = bgpAttrCommunity
            routeindex = routeindex + 1
            routeList.append(routeParams)

        LOG.info('Total Routes = %d' %routeindex)

        updReq = RoutingBgpRouteUpdateRequest(routeList)
        addRes = bgp.BgpRouteUpdate(updReq)
        LOG.info('Invoked Route Add API Status\nreturn = %s' %str(addRes))

        # API reply captured
        statusval = addRes.status
        route_op_count = addRes.operations_completed

        rtmodjsonreply = [{'returncode': str(statusval)}]
        try:
            clrmodsock.send(json.dumps(rtmodjsonreply))
        except:
            LOG.debug("SocketIO: Write failed")

    except:
        rtmodjsonreply = [{'returncode': '104'}]
        try:
            clrmodsock.send(json.dumps(rtmodjsonreply))
        except:
            LOG.debug("SocketIO: Write failed")

    return


def AppRouteDelete(clrdelsock, routereq):

    try:
        # Intialising BGP
        strBgpReq = RoutingBgpRouteInitializeRequest()
        result = bgp.BgpRouteInitialize(strBgpReq)
        LOG.info('Invoked BgpRouteInitialize API return = %s' %str(result))

        # List for route entries to be passed to API
        routeindex = 0
        routeList = list()

        for jsonentry in routereq:
            # Fetching route info from json request
            destroute = jsonentry['ipv4address']
            destroutelst = destroute.split('/')
            DEST_PREFIX_ADD = destroutelst[0]
            DEST_PREFIX_LEN = destroutelst[1]
            DEST_ROUTE_TABLE = 'inet.0'
            LOG.info("Route remove request received for route:%s" %str(destroute))

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
        LOG.info('Invoked Route remove API Status return = %s' %str(remRes))

        # API reply captured
        delstatus = remRes.status
        route_op_count = remRes.operations_completed

        rtaddjsonreply = [{'returncode': str(delstatus)}]
        try:
            clrdelsock.send(json.dumps(rtaddjsonreply))
        except:
            LOG.debug("SocketIO: Write failed")

    except:
        # Condition to handle when API execution was not successful
        rtdeljsonreply = [{'returncode': '103'}]
        try:
            clrdelsock.send(json.dumps(rtdeljsonreply))
        except:
            LOG.debug("SocketIO: Write failed")
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
        LOG.info('Invoked BgpRouteInitialize API return = %s' %str(result.status))
    except Exception as tx:
        LOG.critical('Received exception: %s' % (tx.message))
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
    bgpRouteReq.route_count = '750'
    bgpRouteReq.active_only = False
    try:
        routeGetReply = bgp.BgpRouteGet(bgpRouteReq, topic)
    except Exception as e:
        LOG.critical('Received exception in calling the JET api: %s' % (tx.message))
        eod_data = pack('!ccll',JET_APP_VERSION,'1',0,0)
        clrgetsock.sendall(eod_data)
        os._exit(1)
    responseQ.queue.clear()
    calling_thread_event.wait()
    calling_thread_event.clear()
    LOG.info('Invoked RouteGet API return = %s' %str(routeGetReply))
    getwaitflag = 0
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
                LOG.debug("Unknown request could not be processed")
                LOG.debug("Sending reply to PS")
                jsonreply = [{'returncode': '100'}]
                try:
                    clientsocket.send(json.dumps(jsonreply))
                except:
                    LOG.debug("SocketIO: Write failed")

        except Exception as e:
                LOG.debug("Failed to process the request: %s" %str(e.message))
                LOG.debug("Sending failure reply to PS")
                jsonreply = [{'returncode': '100'}]
                try:
                    clientsocket.send(json.dumps(jsonreply))
                except:
                    LOG.debug("SocketIO: Write failed")
        requestQ.task_done()


try:
    CONNECTION_LIST = list()
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
    LOG.info("Connected to the JET request response server")

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
    LOG.info("Connected to the JET notification server")
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

    port = 8888
    serversocket.bind(('', port))

    LOG.info("Listening to Incoming Connections from the Provisioning Server")
    serversocket.listen(1)
    CONNECTION_LIST.append(serversocket)

    # Variable for capturing thread return
    thvalue = 0
    while True:
        # Establish a incoming connection from Client
        read_sockets,write_sockets,error_sockets = select.select(CONNECTION_LIST,[],[])
        for sock in read_sockets:
            if sock == serversocket:
		if len(CONNECTION_LIST) == 2:
		    LOG.critical('already processing a client')
	        else:
                    sockfd, addr = serversocket.accept()
               	    CONNECTION_LIST.append(sockfd)
                    LOG.info("Client (%s, %s) connected" % addr)
                    LOG.info("Client socket fd = %s" %str(sock))
            else:
                try:
                    # always try to read only the header first if socket not in the dict
                    if sock in sockdict:
                        LOG.info("%s already present in the dictionary, will read bytes = %s" %(str(sock), str(sockdict[sock])))
                    # check for the remaining data to be read
                        psreq = sock.recv(sockdict[sockfd])
                        readlen = len(psreq)
                        if readlen < sockdict[sock]:
                            # need to read again
                            sockdict[sock] -= readlen
                            routereqDict[sock] += psreq
                        else:
                            # complete read done
                            LOG.info('Read completed')
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
                            LOG.info('New Request received of size: %d' %payload_length)
                            sockdict[sock] = payload_length
                            routereqDict[sock] = ''
                except Exception as e:
                    LOG.debug('Exception: %s' %str(e.message))
                    sock.close()
                    CONNECTION_LIST.remove(sock)
                    continue
    serversocket.close()
    requestQ.join()

    # Close session
    evHandle.Unsubscribe()
    LOG.debug("Closing the Client")
    client.CloseRequestResponseSession()
    client.CloseNotificationSession()


except Thrift.TException as tx:
    LOG.critical('Exception received: %s' %(tx.message))
