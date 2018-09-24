"""
Copyright 2018 Juniper Networks Inc.

This JET APP is for Microwave bandwidth notification.
"""

import glob
import os
import re
import sys

import grpc
from pyasn1.codec.ber import decoder
from pysnmp.carrier.asynsock.dispatch import AsynsockDispatcher
from pysnmp.carrier.asynsock.dgram import udp
from pysnmp.carrier.asynsock.dgram import udp6
from pysnmp.proto import api

#for off box compatibility append the location into python path
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'grpc_api'))
import authentication_service_pb2
import mgd_service_pb2

R1 = 'abcd'
APP_USER = 'abcd'
APP_PASSWORD = 'abcd'
IPASO_IP = "10.1.1.1"
IPASO_IF = "ge-0/0/0.0"
ifspeed = "0"
JET_LOCAL_IP = "abcd"
CLIENT_ID = '1212914'
GRPC_PORT = '32767'
#lsp_bw_change ="set protocols mpls label-switched-path lsp1 bandwidth 200m"
lsp_bw_change="""<configuration><protocols><mpls><label-switched-path><name>lsp1</name><bandwidth><per-traffic-class-bandwidth>200m</per-traffic-class-bandwidth></bandwidth></label-switched-path></mpls></protocols></configuration>"""
#lsp_bw_delete = "delete protocols mpls label-switched-path lsp1 bandwidth 200m"
lsp_bw_delete="<configuration><protocols><mpls><label-switched-path><name>lsp1</name><bandwidth delete=\"delete\"></bandwidth></label-switched-path></mpls></protocols></configuration>"


    #Bandwidth management app code flow
    #- Opens session to juniper jet routers
    #- Juniper router running this app listens BW change traps from IPASO devices
    #- Discovers remote juniper JET router IP by invoking jet api
    #- Modifies remote juniper jet router mpls lsp bandwidth to 200M,
    #  if IPASO bw > 200 Mbps or:         
    #- Deletes remote router mpls lsp bandwidth if IPASO bw is < 200 Mbps
    #- Continue to listn to IPASO traps

def _get_data(command_result, req_id):
	for res in command_result:
		if res.request_id == req_id:
			if res.status != mgd_service_pb2.SUCCESS:
					print "ERROR! Something went wrong"
					print res.message
					exit()
			return res.data
	return None
def _authenticateChannel(channel, user, passw, client_id):
    """
    This method authenticates the provided grpc channel.
    """
    sec_stub = authentication_service_pb2.LoginStub(channel)
    cred = authentication_service_pb2.LoginRequest(user_name=user,
                                                   password=passw,
                                                   client_id=client_id)
    res = sec_stub.LoginCheck(cred)
    return res


# Create a channel for connecting to server(JET Router)
channel = grpc.insecure_channel(R1+':'+GRPC_PORT)
res = _authenticateChannel(channel, APP_USER, APP_PASSWORD, "R1C111")
print "Authentication "+('success' if res else 'failure')
if res is False:
    exit()
mgmt_stub = mgd_service_pb2.ManagementRpcApiStub(channel)

# Do the network discovery using mpls lsp statistics
print 'Get MPLS LSP neigbbors'
xml_query = "<get-mpls-lsp-information></get-mpls-lsp-information>"

op_command = mgd_service_pb2.ExecuteOpCommandRequest(request_id=1,
                                                     xml_command=xml_query,
													 out_format=mgd_service_pb2.OPERATION_FORMAT_XML)
command_result = mgmt_stub.ExecuteOpCommand(op_command)
print 'Invoked ExecuteOpCommand \nreturn = '
mgmt_stub2 = None

result1 = _get_data(command_result, 1)

addr1 = re.search(r"<destination-address>(\d+.\d+.\d+.\d+)", result1)
if addr1:
	print "Discovered remote jet router IP address is:", addr1.group(1)
	REMOTE_JET_ROUTE_ADDRESS = addr1.group(1)
	
	# Create a channel for Remote JET Router    
	# Open session with remote jet router JET Server
	# print " Connecting to Management Service"
	channel2 = grpc.insecure_channel(REMOTE_JET_ROUTE_ADDRESS+':'+GRPC_PORT)
	res = _authenticateChannel(channel2, APP_USER, APP_PASSWORD, "R0C112")
	print "Authentication "+('success' if res else 'failure')
	if res is False:
		exit()
	mgmt_stub2 = mgd_service_pb2.ManagementRpcApiStub(channel2)
	print "Listening to IPASO SNMP traps"
else:
	print 'Unable to connect to remote JET router'
	exit()

def bandwidth_monitor_activator(transportDispatcher, transportDomain,transportAddress, wholeMsg):
	"""
	SNMP TRAP Receiver PURE PYTHON CODE
	"""
	global agentaddress, trapname, ifindex, ifspeed    
	# SNMP Trap receiver- listens to IPASO clients for SNMP trap notifications
	while wholeMsg:
		msgVer = int(api.decodeMessageVersion(wholeMsg))
		if msgVer in api.protoModules:
			pMod = api.protoModules[msgVer]
		else:
			print('Unsupported SNMP version %s' % msgVer)
			return
		reqMsg, wholeMsg = decoder.decode(wholeMsg, asn1Spec=pMod.Message())
		print('Notification message from %s:%s: ' % (transportDomain,transportAddress))
		reqPDU = pMod.apiMessage.getPDU(reqMsg)
		if reqPDU.isSameTypeWith(pMod.TrapPDU()):
			if msgVer == api.protoVersion1:
				print('Enterprise: %s' % (
					pMod.apiTrapPDU.getEnterprise(reqPDU).prettyPrint()
					)
					)
				print('Agent Address: %s' % (
					pMod.apiTrapPDU.getAgentAddr(reqPDU).prettyPrint()
					)
					)
				agentaddress = (pMod.apiTrapPDU.getAgentAddr(reqPDU).prettyPrint())
				print('Generic Trap: %s' % (
					pMod.apiTrapPDU.getGenericTrap(reqPDU).prettyPrint()
					)
					)
				trapname = pMod.apiTrapPDU.getGenericTrap(reqPDU).prettyPrint()
				print('Specific Trap: %s' % (
					pMod.apiTrapPDU.getSpecificTrap(reqPDU).prettyPrint()
					)
					)
				print('Uptime: %s' % (
				pMod.apiTrapPDU.getTimeStamp(reqPDU).prettyPrint()
				)
				)
				varBinds = pMod.apiTrapPDU.getVarBindList(reqPDU)

			# Received trap from IPASO
			#Note:(Modify below linkUp trapname with actual ipaso bw_change trapname in NEC setup)
			elif trapname == '\'linkUp\'':
				varBinds = pMod.apiPDU.getVarBindList(reqPDU)
				data = (varBinds.getComponentByPosition(5).getComponentByPosition(1)
							.getComponentByPosition(0).getComponentByPosition(1))
				ifspeed = data.getComponentByPosition(5)
				print 'Received IPASO BW Change snmp trap to: ', ifspeed
				if (IPASO_IP == agentaddress) and (trapname == '\'linkUp\''):
					# Vaidate remote JET IP, incoming interface and modify LSP BW
					# If IPASO Bandwidth is greaterthan 200Mbps then    
					if ifspeed >= 200000000:
						# Validate REMOTE_JET_ROUTE_ADDRESS is reachable via IPASO_IF
						xml_query = "<get-route-information><destination>%s/destination><extensive/></get-route-information>" %REMOTE_JET_ROUTE_ADDRESS
						op_command = mgd_service_pb2.ExecuteOpCommandRequest(request_id=2,
																				xml_command=xml_query,
																				out_format=mgd_service_pb2.OPERATION_FORMAT_XML)
						command_result = mgmt_stub.ExecuteOpCommand(op_command)
						result1 = _get_data(command_result, 2)
						
						intf1 = re.search (r"<via>(\D+-\d+/\d+/\d+\.\d+)", result1)
						if intf1:
							print ('Collected IPASO connected interface name is:',
							intf1.group(1))
							destination_intf = intf1.group(1)
							if destination_intf == IPASO_IF:
								print ('Discovered interface matches IPASO connected'
								'interface')
								xml_query = "<get-mpls-lsp-information><extensive/><regex>lsp1</regex></get-mpls-lsp-information>"
								op_command = mgd_service_pb2.ExecuteOpCommandRequest(request_id=3,
																					xml_command=xml_query,
																					out_format=mgd_service_pb2.OPERATION_FORMAT_XML)
								command_result = mgmt_stub2.ExecuteOpCommand(op_command)
								result2 = _get_data(command_result, 3)
								rbw = re.search (r"<bandwidth>(\d+Mbps)<", result2)
								if rbw:
									print ('Existing remote jet router lsp bandwidth'
													'is:', rbw.group(1))
									rlspbw = rbw.group(1)
									if rlspbw != '200Mbps':
										# Modify MPLS LSP bandwidth
										config_commit = mgd_service_pb2.ConfigCommit(commit_type=mgd_service_pb2.CONFIG_COMMIT,
																						comment="setting mpls bandwidth")
										config = ExecuteCfgCommandRequest(request_id=4,
																			xml_config=lsp_bw_change,
																			load_type=mgd_service_pb2.CONFIG_LOAD_MERGE,
																			commit=config_commit)
										result3 = mgmt_stub2.ExecuteCfgCommand(config)
										if result3.status == mgd_service_pb2.SUCCESS:
											print ('Modified remote JET router MPLS' 
															'lsp bandwidth to 200 mbps \n')
										else:
											print result3.message
									else:
										print ('Bandwidth configs exists in remote'
															'jet router hence No changes required \n')
								else:
									config_commit = mgd_service_pb2.ConfigCommit(commit_type=mgd_service_pb2.CONFIG_COMMIT,
																					comment="setting mpls bandwidth")
									config = ExecuteCfgCommandRequest(request_id=4,
																		xml_config=lsp_bw_change,
																		load_type=mgd_service_pb2.CONFIG_LOAD_MERGE,
																		commit=config_commit)
									result3 = mgmt_stub2.ExecuteCfgCommand(config)
									if result3.status != mgd_service_pb2.SUCCESS
										print "Something went wrong"
										print result3.message
									else:
										print ('lsp bw is null hence modified remote' 
												'JET Router MPLS Bandwidth to 200 mbps  \n')
							else:
								print 'Does not match to IPASO connected interface \n'
						else:
							print 'Unable to collect IPASO connected interface \n'
					# Revert changes in remote JET router if BW is lessthan 200Mbps 
					else:
						print 'IPASO bandwidth is lessthan 200Mbps \n'
						# verify remote JET router MPLS lsp bandwidth configurations
						xml_query = "<get-mpls-lsp-information><extensive/><regex>lsp1</regex></get-mpls-lsp-information>"
						op_command = mgd_service_pb2.ExecuteOpCommandRequest(request_id=5,
																			xml_command=xml_query,
																			out_format=mgd_service_pb2.OPERATION_FORMAT_XML)
						command_result = mgmt_stub2.ExecuteOpCommand(op_command)
						result4 = _get_data(command_result, 5)
						
						rbw1 = re.search (r"<bandwidth>(\d+Mbps)<", result4)
						if rbw1:
							print ('Remote jet router current mpls lsp bandwidth is:',
										rbw1.group(1))
							rlspbw = rbw1.group(1)
							if rlspbw == '200Mbps':
								print ('LSP bw is 200 Mbps hence bandwidth parameters'
												'to be modified in remote JET router \n')
								# Delete MPLS LSP bandwidth
								config_commit = mgd_service_pb2.ConfigCommit(commit_type=mgd_service_pb2.CONFIG_COMMIT,
																					comment="setting mpls bandwidth")
								config = ExecuteCfgCommandRequest(request_id=6,
																	xml_config=lsp_bw_delete,
																	load_type=mgd_service_pb2.CONFIG_LOAD_REPLACE,
																	commit=config_commit)
								result3 = mgmt_stub2.ExecuteCfgCommand(config)
								if result3.status == mgd_service_pb2.SUCCESS:
									print ('Deleted remote JET router MPLS lsp bandwidth'
													'and listening to IPASO bw change notification\n')
								else:
									print result3.message
							else:
								print 'listening to IPASO bw change notification \n'
						else:
							print 'No changes required in remote jet lsp  \n'
			else:
				print 'No action required as received trap is generic'
		else:
		    print 'No action required as received trap is generic'
	return wholeMsg

transportDispatcher = AsynsockDispatcher()

transportDispatcher.registerRecvCbFun(bandwidth_monitor_activator)

# UDP/IPv4 Juniper JET Router management IP
transportDispatcher.registerTransport(
    udp.domainName, udp.UdpSocketTransport().openServerMode((JET_LOCAL_IP, 162))
)

transportDispatcher.jobStarted(1)

try:
    # Dispatcher will never finish as job#1 never reaches zero
    transportDispatcher.runDispatcher()
except:
    transportDispatcher.closeDispatcher()
    raise
