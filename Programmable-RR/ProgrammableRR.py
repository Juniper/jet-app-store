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
Copyright 2018 Juniper Networks Inc
Sample application to handle the requests for setting and getting of BGP routes using
JET infra on JUNOS devices. This app acts as a server/forwarder for requests from a
Provisional Server (PS) client.This app can handle at most two concurrent requests so that
this app can be used on-box on low-end JUNOS routers and it cannot be two concurrent GET requests.
This app listens to requests from PS for BGP route add, modify, delete and
get requests. The requests have to be provided by the PS in JSON format.

In case of GET requests, this app will respond to the PS in the following message format:
|-------------------------------------------------------------------------------|
| 1byte version| 1 byte response status || 4 byte Payload length | 4 byte unused|
|<----------------------------------------------------------------------------->|
|                                 Payload Message                               |
|-------------------------------------------------------------------------------|

Last message sent by this app will carry 0 payload length. In case, GET requests encounter any
error from the JUNOS router, then in that case, response status will be non-zero. This
should be a condition to exit the recv loop in the PS client.
"""


import socket, select
from struct import *
import logging
from logging.handlers import RotatingFileHandler
import time
from Queue import Queue
from threading import Thread
import threading
import json
import struct

from grpc.beta import implementations
from grpc.framework.interfaces.face.face import *

import authentication_service_pb2
import bgp_route_service_pb2
import prpd_service_pb2
import prpd_common_pb2
import jnx_addr_pb2
from authentication_service_pb2 import *
from bgp_route_service_pb2 import *
from prpd_service_pb2 import *
from prpd_common_pb2 import *
from jnx_addr_pb2 import *

# Logging Parameters
DEFAULT_LOG_FILE_NAME = '/tmp/jetapp.log'
#DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_LEVEL = logging.DEBUG
#DEFAULT_LOG_LEVEL = logging.CRITICAL

# Enable Logging to a file
FORMAT = "[%(filename)s:%(lineno)s - %(funcName)s ] %(message)s"
logging.basicConfig(filename=DEFAULT_LOG_FILE_NAME, level=DEFAULT_LOG_LEVEL, format = FORMAT)
handler = RotatingFileHandler(DEFAULT_LOG_FILE_NAME,maxBytes=1024)
LOG = logging.getLogger(__name__)
LOG.addHandler(handler)

# Variables for THRIFT/MQTT connection
HOST = '10.209.15.207'
GRPC_PORT = 32767
PORT = 9090
CLIENT_ID = "102"
USER = 'user_name'
PASSWORD = 'password'
TIMEOUT = 250
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
            #responseQ.task_done()
            # Verify if the entry in the Q is the end of the messages
            # if not then process it
            if (rspMsg == 'END_OF_DATA'):
                eod_data = pack('!ccll',JET_APP_VERSION,'1',0,0)
                try:
                    LOG.critical("Read EOD info from the Q")
                    clrgetsock.sendall(str(eod_data))
                    calling_thread_event.set()
                except socket.error, (value, message):
                    getwaitflag = 1
                    LOG.debug('socket.error in sending eod - %s' %str(message))
                    calling_thread_event.set()
            else:
                str_res = rspMsg
                if (str_res.status == 0):
                    bgpRouteEntry = str_res.bgp_routes
                    json_data = "["

                    for route in bgpRouteEntry:
                        try:
                            nh6str = route.protocol_nexthops[0].addr_string
                        except Exception as e:
                            nh6str = "None"
                            LOG.debug('Next-Hop not found for the route')
                        try:
                            ro_comm = route.communities.com_list[0].community_string
                        except Exception as e:
                            ro_comm = "None"
                            LOG.debug("Route community not found for the route")

                        json_data += "{'ipv4address':'" + str(route.dest_prefix.inet.addr_string) + "/" + str(route.dest_prefix_len) + "', 'ipv6nh':'" + str(nh6str) + "', 'community':'" + str(ro_comm) + "' },"

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
                    LOG.critical("Route Entry didnt have route information")
                    LOG.critical('Value of Route Status.. = %s' %str(str_res.status))
                    LOG.debug('Value of Status..\nreturn = %s ' %str(str_res.status))
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
        responseQ.put((message))
        time.sleep(2)


def AppRouteAdd(clientsocket, routereq):

    try:
        # Intialising BGP
        LOG.info('Invoked BgpRouteInitialize API inside AppRouteAdd..') 
        strBgpReq = BgpRouteInitializeRequest()
        result = bgp.BgpRouteInitialize(strBgpReq, TIMEOUT)
        LOG.info('Invoked BgpRouteInitialize API inside AppRouteAdd.. \nreturn = %s ' %str(result.status))
        # List for route entries to be passed to API
        routeindex = 0
        routeList = list()

        for jsonentry in routereq:
            # Fetching route info from json request
            destroute = jsonentry['ipv4address']
            destroutelst = destroute.split('/')
            DEST_PREFIX_ADD = destroutelst[0]
            DEST_PREFIX_LEN = int(destroutelst[1])
            DEST6_NEXT_HOP = jsonentry['ipv6nh']
            Community_1 = jsonentry['community']
            LOG.info("Route add request received for route:%s" % str(destroute))

            # Preparing parameters to call BGP Update API
            DEST_ROUTE_TABLE = 'inet.0'
            Protocol = 2
            destPrefix = RoutePrefix(inet=IpAddress(addr_string=DEST_PREFIX_ADD))
            destTable = RouteTable(rtt_name=RouteTableName(name=DEST_ROUTE_TABLE))
            nextHop = IpAddress(addr_string=DEST6_NEXT_HOP)
            comm1 = Community(community_string=Community_1)
            cmList = CommunityList(com_list=[comm1])
            routeParams = BgpRouteEntry(dest_prefix=destPrefix, dest_prefix_len=DEST_PREFIX_LEN, table=destTable,protocol_nexthops=[nextHop], protocol=Protocol, communities=cmList)
            routeindex = routeindex + 1
            routeList.append(routeParams)

        LOG.info('Total Routes = %d' % routeindex)

        # Calling BGP Route Add API to program routes
        updReq = BgpRouteUpdateRequest(bgp_routes=routeList)
        addRes = bgp.BgpRouteAdd(updReq, TIMEOUT)
        LOG.info('Invoked Route Add API Status\nreturn = %s' % str(addRes))

        # API reply captured
        statusval = addRes.status
        route_op_count = addRes.operations_completed

        LOG.info("Sending reply to PS")
        rtaddjsonreply = [{'returncode': str(statusval), 'route_op_count': str(route_op_count)}]
        try:
            clientsocket.send(json.dumps(rtaddjsonreply))
        except:
            LOG.debug("SocketIO: Write failed")

    except Exception as e:
        LOG.info(str(e))        
        LOG.debug('Error in Route Add Request')
        LOG.debug('Sending error-code to PS')
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
        LOG.info('Invoked BgpRouteInitialize API inside AppRouteModify..')
        strBgpReq = BgpRouteInitializeRequest()
        result = bgp.BgpRouteInitialize(strBgpReq, TIMEOUT)
        LOG.info('Invoked BgpRouteInitialize API inside AppRouteModify.. \nreturn = %s ' % str(result.status))
        # List for route entries to be passed to API
        routeindex = 0
        routeList = list()

        for jsonentry in routereq:
            # Fetching route info from json request
            destroute = jsonentry['ipv4address']
            destroutelst = destroute.split('/')
            DEST_PREFIX_ADD = destroutelst[0]
            DEST_PREFIX_LEN = int(destroutelst[1])
            DEST6_NEXT_HOP = jsonentry['ipv6nh']
            Community_1 = jsonentry['community']
            LOG.info("Route Modify request received for route: %s" % str(destroute))

            # Preparing parameters to call BGP Update API
            DEST_ROUTE_TABLE = 'inet.0'
            Protocol = 2
            destPrefix = RoutePrefix(inet=IpAddress(addr_string=DEST_PREFIX_ADD))
            destTable = RouteTable(rtt_name=RouteTableName(name=DEST_ROUTE_TABLE))
            nextHop = IpAddress(addr_string=DEST6_NEXT_HOP)
            comm1 = Community(community_string=Community_1)
            cmList = CommunityList(com_list=[comm1])
            routeParams = BgpRouteEntry(dest_prefix=destPrefix, dest_prefix_len=DEST_PREFIX_LEN, table=destTable,protocol_nexthops=[nextHop], protocol=Protocol, communities=cmList)
            routeindex = routeindex + 1
            routeList.append(routeParams)

        LOG.info('Total Routes = %d' % routeindex)

        # Calling BGP Route Update API to modify routes
        updReq = BgpRouteUpdateRequest(bgp_routes=routeList)
        addRes = bgp.BgpRouteUpdate(updReq, TIMEOUT)
        LOG.info('Invoked Route Modify API Status\nreturn = %s' % str(addRes))

        # API reply captured
        statusval = addRes.status
        route_op_count = addRes.operations_completed

        LOG.info("Sending reply to PS")
        rtmodjsonreply = [{'returncode': str(statusval), 'route_op_count': str(route_op_count)}]
        try:
            clrmodsock.send(json.dumps(rtmodjsonreply))
        except:
            LOG.debug("SocketIO: Write failed")

    except Exception as e:
        LOG.info(str(e)) 
        LOG.debug('Error in Route Modify Request')
        LOG.debug("Sending error-code to PS")
        rtmodjsonreply = [{'returncode': '104'}]
        try:
            clrmodsock.send(json.dumps(rtmodjsonreply))
        except:
            LOG.debug("SocketIO: Write failed")

    return



def AppRouteDelete(clrdelsock, routereq):

    try:
        # Intialising BGP
        LOG.info('Invoked BgpRouteInitialize API inside AppRouteDelete..')
        strBgpReq = BgpRouteInitializeRequest()
        result = bgp.BgpRouteInitialize(strBgpReq, TIMEOUT)
        LOG.info('Invoked BgpRouteInitialize API inside AppRouteDelete.. \nreturn = %s ' %str(result.status))

        # List for route entries to be passed to API
        routeindex = 0
        routeList = list()

        for jsonentry in routereq:
            # Fetching route info from json request
            destroute = jsonentry['ipv4address']
            destroutelst = destroute.split('/')
            DEST_PREFIX_ADD = destroutelst[0]
            DEST_PREFIX_LEN = int(destroutelst[1])
            DEST_ROUTE_TABLE = 'inet.0'
            Path_Cookie = 11
            LOG.info("Route remove request received for route:%s" % str(destroute))
            # Preparing parameters to call BGP Route Remove API
            destPrefix = RoutePrefix(inet=IpAddress(addr_string=DEST_PREFIX_ADD))
            destTable = RouteTable(rtt_name=RouteTableName(name=DEST_ROUTE_TABLE))
            routeParams = BgpRouteMatch(dest_prefix=destPrefix, dest_prefix_len=DEST_PREFIX_LEN, table=destTable)
            routeindex = routeindex + 1
            routeList.append(routeParams)

        LOG.info('Total Routes = %d' % routeindex)

        # Calling BGP Route Remove API to delete routes
        remReq = BgpRouteRemoveRequest(or_longer=0, bgp_routes=routeList)
        remRes = bgp.BgpRouteRemove(remReq,TIMEOUT )
        LOG.info('Invoked Route remove API Status return = %s' % str(remRes))

        # API reply captured
        delstatus = remRes.status
        route_op_count = remRes.operations_completed

        rtaddjsonreply = [{'returncode': str(delstatus), 'route_op_count': str(route_op_count)}]
        try:
            clrdelsock.send(json.dumps(rtaddjsonreply))
        except:
            LOG.debug("SocketIO: Write failed")

    except:
        LOG.info(str(e))
        LOG.debug('Error in Route Delete Request')
        LOG.debug("Sending error-code to PS")
        rtdeljsonreply = [{'returncode': '103'}]
        try:
            clrdelsock.send(json.dumps(rtdeljsonreply))
        except:
            LOG.debug("SocketIO: Write failed")
    return


def AppRouteGet(clrgetsock, routereq):
    # Flag to indicate that the disptach thread execution is complete
    global getwaitflag
    global calling_thread_event
    getwaitflag = 0
    # Intialising BGP
    try:
        strBgpReq = BgpRouteInitializeRequest()
        result = bgp.BgpRouteInitialize(strBgpReq, TIMEOUT)
        LOG.info('Invoked BgpRouteInitialize API return = %s' % str(result.status))
    except Exception as tx:
        LOG.critical('Received exception: %s' % (tx.message))
        eod_data = pack('!ccll', JET_APP_VERSION, '1', 0, 0)
        clrgetsock.sendall(eod_data)
        os._exit(1)

    LOG.debug("Received Route Query Request")
    DEST_ROUTE_TABLE = 'inet.0'
    destprefix = RoutePrefix(inet=IpAddress(addr_string='0.0.0.0'))
    rttable = RouteTable(rtt_name=RouteTableName(name=DEST_ROUTE_TABLE))
    routeParams = BgpRouteMatch(dest_prefix=destprefix, dest_prefix_len=0, protocol=2, table=rttable)
    bgpRouteReq = BgpRouteGetRequest(bgp_route=routeParams, or_longer=True, active_only=False, route_count=750)

    try:
        routeGetReply = bgp.BgpRouteGet(bgpRouteReq, timeout=5460)
    except Exception as e:
        LOG.critical('Received exception in calling the JET api: %s' % (tx.message))
        eod_data = pack('!ccll', JET_APP_VERSION, '1', 0, 0)
        clrgetsock.sendall(eod_data)
        os._exit(1)

    route_counter = 0
    for i in routeGetReply:
        route_counter = route_counter + 1
        LOG.critical(route_counter)
        responseQ.put(i)
        #time.sleep(2)

    # After inserting all the routes we need to insert END_OF_DATA for
    # dispatcher Queue to stop.
    LOG.critical("Route Streaming Completed")
    LOG.critical(route_counter)
    responseQ.put("END_OF_DATA")
    calling_thread_event.wait()
    calling_thread_event.clear()
    getwaitflag = 0
    if not responseQ.empty():
        responseQ.queue.clear()
    return

def allRouteApis():
    while True:
        routereq, clientsocket = requestQ.get()
        LOG.info('Request Finder')
        try:
            if(routereq[0]['action'] == 'add'):
                LOG.info('Request is for Add')
                thvalue = AppRouteAdd(clientsocket, routereq)

            elif(routereq[0]['action'] == 'query'):
                global clrgetsock
                clrgetsock = clientsocket
                LOG.info('Request is for Query')
                thvalue = AppRouteGet(clrgetsock, routereq)

            elif(routereq[0]['action'] == 'delete'):
                global clrdelsock
                clrdelsock = clientsocket
                LOG.info('Request is for Delete')
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
                LOG.info(str(e))
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

    channel = implementations.insecure_channel(host=HOST, port=GRPC_PORT)
    stub = authentication_service_pb2.beta_create_Login_stub(channel)
    login_response = stub.LoginCheck(authentication_service_pb2.LoginRequest(user_name=USER, password=PASSWORD, client_id=CLIENT_ID), TIMEOUT)
    LOG.info("Connected to the JET GRPC request response server")

    bgp = bgp_route_service_pb2.beta_create_BgpRoute_stub(channel)
    prpd = prpd_service_pb2.beta_create_Base_stub(channel)


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
                    LOG.debug('Already processing a client')
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
			    LOG.info(str(routereq))
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
    LOG.critical("Closing the Client")
    client.CloseRequestResponseSession()
    client.CloseNotificationSession()


except Thrift.TException as tx:
    LOG.critical('Exception received: %s' %(tx.message))

