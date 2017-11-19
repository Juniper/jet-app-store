#!/usr/bin/env python
#Copyright 2017 Juniper Networks, Inc. All rights reserved.
#Licensed under the Juniper Networks Script Software License (the "License"). 
#You may not use this script file except in compliance with the License, which is located at 
#http://www.juniper.net/support/legal/scriptlicense/
#Unless required by applicable law or otherwise agreed to in writing by the parties, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.


from grpc.beta import implementations
import mgd_service_pb2
import authentication_service_pb2
import docker
import json
import time
from lxml import etree

# Device details and login credentials
JSD_IP = '127.0.0.1'   # Update with your device name/IP
JSD_PORT = 32767  
USERNAME = 'xxxx'       # Update with your device login details
PASSWORD = 'xxxxx'       # Update with your device login details
CLIENT_ID = 'demo'
_TIMEOUT_SECONDS = 20

def EstablishChannel(address, port, client_id, user, password):
    # Open a grpc channel to the device
    #creds = implementations.ssl_channel_credentials(open('/tmp/host.pem').read(), None, None)
    channel = implementations.insecure_channel(address, port)

    # Create stub for authentication
    login_stub = authentication_service_pb2.beta_create_Login_stub(channel)

    # Fill the login request message structure
    login_request = authentication_service_pb2.LoginRequest(user_name=user, password=password, client_id=client_id)

    # Invoke the login check API
    login_response = login_stub.LoginCheck(login_request, _TIMEOUT_SECONDS)
    
    return channel

def getSocket(hostName, parsedResponse):

    hostName = hostName
    socketHost = 'Unknown'
    socketRemote = 'Unknown'    
    index = 0
    
    for neighbor in parsedResponse['lldp-neighbors-information']:
        for neighborInfo in neighbor['lldp-neighbor-information']:
            for system in neighborInfo['lldp-remote-system-name']:
                if system['data'] == hostName:
                    socketHost = parsedResponse['lldp-neighbors-information'][0]['lldp-neighbor-information'][index]['lldp-remote-port-description'][0]['data']
                    socketRemote = parsedResponse['lldp-neighbors-information'][0]['lldp-neighbor-information'][index]['lldp-local-port-id'][0]['data']
                index += 1
    
    return socketHost, socketRemote

def printContainers(client, channel):
    
    xml_items = []
    servicesList = client.services.list()
    socketRemoteMap = {}
    socketHostMap = {}
    # Create a stub for Management RPC
    stub = mgd_service_pb2.beta_create_ManagementRpcApi_stub(channel)
    # Execute ExecuteOpCommand RPC
    executeOpCommandrequest = mgd_service_pb2.ExecuteOpCommandRequest(cli_command="show lldp neighbors",
                                                                      out_format=mgd_service_pb2.OPERATION_FORMAT_JSON,
                                                                      request_id=1000)
    response = stub.ExecuteOpCommand(executeOpCommandrequest, _TIMEOUT_SECONDS)    
    for responseA in response:
        parsedResponse = json.loads(responseA.data)
        break

    
    print "%-45s\t\t%-15s\t%-15s\t\t%-15s\t%-15s\t%-15s" % ("NODE","SERVICE NAME","CONTAINER ID",
                                                            "PORTS","SWITCH PHYSICAL PORT", "SERVER PHYSICAL PORT") 
    for service in servicesList:
        port = "None"
        bridge = "bridge"
        socketHost = socketRemote = "Unknown"
        if len(service.attrs['Spec']['EndpointSpec'].items()) > 1: # If there are (exposed/published) ports
                port = ""
                for p in service.attrs['Spec']['EndpointSpec'].items()[1][1]:
                    port = port + "+%s:%s/%s" % (p['TargetPort'], p['PublishedPort'], p['Protocol'])
                port = port[1:]
        for task in service.tasks(): 
            if task['Status']['State'] == "running":
                NodeID = task['NodeID']
                Hostname = client.nodes.get(NodeID).attrs['Description']['Hostname']
                ContainerID = task['Status']['ContainerStatus']['ContainerID']
                if Hostname not in socketRemoteMap:
                    socketHost, socketRemote = socketHostMap[Hostname], socketRemoteMap[Hostname] = getSocket(Hostname, parsedResponse)
                else:
                    socketHost, socketRemote = socketHostMap[Hostname], socketRemoteMap[Hostname]
                
                xml_item = etree.Element('container-info')
                xml_hostname = etree.SubElement(xml_item, 'hostname')
                xml_hostname.text = Hostname
                xml_service = etree.SubElement(xml_item, 'service')
                xml_service.text = service.name
                xml_containerID = etree.SubElement(xml_item, 'containerID')
                xml_containerID.text = ContainerID[:16]
                xml_port = etree.SubElement(xml_item, 'port')
                xml_port.text = port
                xml_socketRemote = etree.SubElement(xml_item, 'socketRemote')
                xml_socketRemote.text = socketRemote
                xml_socketHost = etree.SubElement(xml_item, 'socketHost')
                xml_socketHost.text = socketHost
                xml_items.append(xml_item)

                print "%-45s\t\t%-15s\t%-15s\t%-15s\t%-15s\t\t%-15s" % (Hostname, service.name, ContainerID[:16], 
                                                       port, socketRemote, socketHost)

    return xml_items

def Main():
    cli = docker.DockerClient(base_url="tcp://10.92.70.225:2375")
    channel = EstablishChannel(JSD_IP, JSD_PORT, CLIENT_ID, USERNAME, PASSWORD)
    xml_items = printContainers(cli, channel)
    xml = etree.Element('docker-container-info')
    for xml_item in xml_items:
        xml.append(xml_item)
    #print(etree.tostring(xml, pretty_print=True))

if __name__ == '__main__':
    t0 = time.time()
    Main()
    t1 = time.time()
    total = t1 - t0
    #print total
