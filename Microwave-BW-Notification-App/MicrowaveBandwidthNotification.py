from pysnmp.carrier.asynsock.dispatch import AsynsockDispatcher
from pysnmp.carrier.asynsock.dgram import udp, udp6
from pyasn1.codec.ber import decoder
from pysnmp.proto import api
import sys, os, re, glob
import re
from juniper.jet.JetHandler import JetHandler
from juniper.jet.ttypes import *        

R1 = 'r1k'
APP_USER = 'user1'
APP_PASSWORD = 'password1'
IPASO_IP = "10.255.209.176"
IPASO_IF = "ge-0/0/0.0"
ifspeed = "0"
JET_LOCAL_IP = "10.216.192.161"
lsp_bw_change = """
	set protocols mpls label-switched-path lsp1 bandwidth 200m
"""
lsp_bw_delete = """
	delete protocols mpls label-switched-path lsp1 bandwidth 200m
    """
    
    #Bandwidth management app code flow
    #- Opens session to juniper jet routers
    #- Juniper router running this app listens BW change traps from IPASO devices
    #- Discovers remote juniper JET router IP by invoking jet api
    #- Modifies remote juniper jet router mpls lsp bandwidth to 200M,
    #  if IPASO bw > 200 Mbps or:         
    #- Deletes remote router mpls lsp bandwidth if IPASO bw is < 200 Mbps
    #- Continue to listn to IPASO traps
    
# Create a client handler for connecting to server(JET Router)
client = JetHandler()

# Open session with Thrift Servers
client.OpenRequestResponseSession(device=R1, connect_timeout=300000, user=APP_USER, password=APP_PASSWORD, client_id= "R1C111")
print "\nEstablished connection with the", R1

print " Connecting to  Management Service"
mgmt_handle = client.GetManagementService()

# Do the network discovery using mpls lsp statistics    
print 'Get MPLS LSP neigbbors'
xml_query = "<get-mpls-lsp-information></get-mpls-lsp-information>"
    op_command = OperationCommand(xml_query, in_format=OperationFormatType.OPERATION_FORMAT_XML,
                                            out_format=OperationFormatType.OPERATION_FORMAT_XML);
result = mgmt_handle.ExecuteOpCommand(opcommand)
print 'Invoked ExecuteOpCommand \nreturn = '
addr1 = re.search (r"<destination-address>(\d+.\d+.\d+.\d+)", result)
if addr1:
    print "Discovered remote jet router IP address is:", addr1.group(1)
    REMOTE_JET_ROUTE_ADDRESS = addr1.group(1)
    
    # Create a client handler for Remote JET Router    
    client2 = JetHandler()
    
    # Open session with remote jet router JET Server
    client.OpenRequestResponseSession(device=REMOTE_JET_ROUTE_ADDRESS, connect_timeout=300000, user=APP_USER, password=APP_PASSWORD, client_id= "R0C112")
    
    print " Connecting to  Management Service"
    mgmt_handle2 = client2.GetManagementService()
    print "Listening to IPASO SNMP traps"
  
else:
    print 'Unable to connect to remote JET router'
    
#SNMP TRAP Receiver PURE PYTHON CODE
def bandwidth_monitor_activator(transportDispatcher, transportDomain,transportAddress, wholeMsg):
    global agentaddress, trapname, ifindex, ifspeed    
  
    # SNMP Trap receiver- listens to IPASO clients for SNMP trap notifications
    while wholeMsg:
	msgVer = int(api.decodeMessageVersion(wholeMsg))
	if msgVer in api.protoModules:
	    pMod = api.protoModules[msgVer]
	else:
	    print('Unsupported SNMP version %s' % msgVer)
	    return
	reqMsg, wholeMsg = decoder.decode(
	    wholeMsg, asn1Spec=pMod.Message(),
	    )
	print('Notification message from %s:%s: ' % (
	    transportDomain, transportAddress
	    )
	)
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
		#print('%s = %s' % (oid.prettyPrint(),val.prettyPrint()))
		print 'Received IPASO BW Change snmp trap to: ', ifspeed
		if (IPASO_IP == agentaddress) and (trapname == '\'linkUp\''):
		      
		    # Vaidate remote JET IP, incoming interface and modify LSP BW
                    # If IPASO Bandwidth is greaterthan 200Mbps then    
		    if ifspeed >= 200000000:
		    
			# Validate REMOTE_JET_ROUTE_ADDRESS is reachable via IPASO_IF
            xml_query = "<get-route-information><destination>%s/destination><extensive/></get-route-information>" %REMOTE_JET_ROUTE_ADDRESS
            op_command = OperationCommand(xml_query, in_format=OperationFormatType.OPERATION_FORMAT_XML,
                                            out_format=OperationFormatType.OPERATION_FORMAT_XML);
			result1 = mgmt_handle.ExecuteOpCommand(op_comand)   
			intf1 = re.search (r"<via>(\D+-\d+/\d+/\d+\.\d+)", result1)
			if intf1:
			    print ('Collected IPASO connected interface name is:',
                            intf1.group(1))
			    destination_intf = intf1.group(1)
			    if destination_intf == IPASO_IF:
				print ('Discovered interface matches IPASO connected'
                                'interface')
                xml_query = "<get-mpls-lsp-information><extensive/><regex>lsp1</regex></get-mpls-lsp-information>"
                op_command = OperationCommand(xml_query, in_format=OperationFormatType.OPERATION_FORMAT_XML,
                                            out_format=OperationFormatType.OPERATION_FORMAT_XML);
				result2 = mgmt_handle2.ExecuteOpCommand(op_command)   
				rbw = re.search (r"<bandwidth>(\d+Mbps)<", result2)
				if rbw:
				    print ('Existing remote jet router lsp bandwidth'
                                    'is:', rbw.group(1))
				    rlspbw = rbw.group(1)
				    if rlspbw != '200Mbps':
				    
				# Modify MPLS LSP bandwidth
                    config = ConfigLoadCommit(lsp_bw_change,ConfigFormatType.CONFIG_FORMAT_SET, ConfigDatabaseType.CONFIG_DB_SHARED,
                              ConfigLoadType.CONFIG_LOAD_REPLACE, commit)
					result3 = mgmt_handle2.ExecuteCfgCommand(config)
					print ('Modified remote JET router MPLS' 
                                        'lsp bandwidth to 200 mbps \n')
				    else:
					print ('Bandwidth configs exists in remote'
                                        'jet router hence No changes required \n')
				else:
                    config = ConfigLoadCommit(lsp_bw_change,ConfigFormatType.CONFIG_FORMAT_SET, ConfigDatabaseType.CONFIG_DB_SHARED,
                              ConfigLoadType.CONFIG_LOAD_REPLACE, commit)
				    result13 = mgmt_handle2.ExecuteCfgCommand(config)
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
            op_command = OperationCommand(xml_query, in_format=OperationFormatType.OPERATION_FORMAT_XML,
                                            out_format=OperationFormatType.OPERATION_FORMAT_XML);
			result4 = mgmt_handle2.ExecuteOpCommand(op_command)   
			rbw1 = re.search (r"<bandwidth>(\d+Mbps)<", result4)
			if rbw1:
			    print ('Remote jet router current mpls lsp bandwidth is:',
                            rbw1.group(1))
			    rlspbw = rbw1.group(1)
			    if rlspbw == '200Mbps':
				print ('LSP bw is 200 Mbps hence bandwidth parameters'
                                'to be modified in remote JET router \n')
				
				# Delete MPLS LSP bandwidth
                config = ConfigLoadCommit(lsp_bw_delete,ConfigFormatType.CONFIG_FORMAT_SET, ConfigDatabaseType.CONFIG_DB_SHARED,
                              ConfigLoadType.CONFIG_LOAD_REPLACE, commit)
				result5 = mgmt_handle2.ExecuteCfgCommand(config)
				print ('Deleted remote JET router MPLS lsp bandwidth'
                                'and listening to IPASO bw change notification\n')
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
