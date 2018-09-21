#!/usr/bin/env python
import re
import traceback
import argparse
import grpc
import authentication_service_pb2
import jnx_addr_pb2
from rib_service_pb2 import *
import prpd_common_pb2
import rib_service_pb2 as Route
import utility
import grpc
from grpc.beta import implementations
from grpc.framework.interfaces.face.face import *
from authentication_service_pb2 import *
import authentication_service_pb2

try:
    from management_service_pb2 import *
except  ImportError:
    from mgd_service_pb2 import *
try:
    import management_service_pb2
except ImportError:
    import mgd_service_pb2 as management_service_pb2

#VARIABLES
#R1 = 'router'
#r1_interface = 'ge-0/0/0.0'
#username = 'user'
#user_password = 'user_pwd'
#grpc_port = '32767'
#DIP = '192.168.20.1/32'
#NIP = '172.16.2.2'
#CLIENT_ID = '1212914'
#route_table_name = 'inet.0'
#route_prefix= '192.168.20.1'

Route_stub = None
route_present = None
def main():
    try:
        global route_stub, R1, r1_interface, username, user_password, grpc_port, NIP, DIP, CLIENT_ID, route_table_name, route_prefix, r1_interface_SNMP_INDEX
        parser = argparse.ArgumentParser()
        parser.add_argument('-R1',help="Hostname or ip",type=str )
        parser.add_argument('-r1_interface',help="Interface name to monitor(IFL)",type=str)
        parser.add_argument('-username', help="Username for device",type=str)
        parser.add_argument('-user_password', help="Password for device",type=str)
        parser.add_argument('-grpc_port', help="GRPC port number",type=str)
        parser.add_argument('-NIP', help="Nexthop ip",type=str)
        parser.add_argument('-DIP', help="Destination ip",type=str)
        parser.add_argument('-CLIENT_ID', help="client id",type=str)
        parser.add_argument('-route_table_name', help="route table name",type=str)
        parser.add_argument('-route_prefix', help="default route prix",type=str)
        args, unknown = parser.parse_known_args()
    
        R1 = args.R1 or R1
        r1_interface = args.r1_interface or r1_interface
        username = args.username or username
        user_password = args.user_password or user_password
        grpc_port = args.grpc_port or grpc_port
        NIP = args.NIP or NIP
        DIP = args.DIP
        CLIENT_ID = args.CLIENT_ID or CLIENT_ID
        route_table_name = args.route_table_name or route_table_name
        route_prefix= args.route_prefix or route_prefix
        
        print "Creating GRPC Channel"
        channel = grpc.insecure_channel(R1+':'+grpc_port)
        
        print "GRPC Channel Authentication check"
        res = _authenticateChannel(channel, username, user_password, CLIENT_ID)
        print "Authentication "+('success' if res else 'failure')
        if res is False:
            return
        
        print "Creating Managment Srvice STUB"
        mgd = management_service_pb2.ManagementRpcApiStub(channel) 
        
        op_command = "show interfaces "+r1_interface+" detail"
        op = ExecuteOpCommandRequest(cli_command = op_command, out_format = 2, request_id = 1000)
        result = mgd.ExecuteOpCommand(op,timeout=60)
        response = ""
        for i in result:
            response += i.data
        if i.status == 0:
            print 'Invoked ExecuteOpCommand API return code = ', i.status
        else:
            print 'Something went Wrong !!! Data not received'

        SNMP_INDEX = re.search(r'.*Logical interface ' + re.escape(r1_interface) + r"\s\(\w+\s\d+\)\s+\(SNMP ifIndex\s(\d+)\)",response,re.DOTALL)
        r1_interface_SNMP_INDEX = SNMP_INDEX.group(1)
        print "SNMP_INDEX Value of monitoring IFL_interface:",r1_interface,r1_interface_SNMP_INDEX
    
        
        print "Configuring SNMP CONFIG"
        SET_SNMP_CONFIG="""<configuration-set>
                            delete snmp rmon alarm 1
                            edit snmp rmon
                            set alarm 1 interval 1
                            set alarm 1 variable ifIn1SecRate."""+r1_interface_SNMP_INDEX+"""
                            set alarm 1 sample-type absolute-value
                            set alarm 1 request-type get-request
                            set alarm 1 rising-threshold 1024
                            set alarm 1 falling-threshold 1023
                            set alarm 1 rising-event-index """+r1_interface_SNMP_INDEX+"""
                            set alarm 1 falling-event-index """+r1_interface_SNMP_INDEX+"""
                            set alarm 1 falling-event-index """+r1_interface_SNMP_INDEX+"""
                            set alarm 1 syslog-subtag IFINDEX"""+r1_interface_SNMP_INDEX+"""
                            set event """+r1_interface_SNMP_INDEX+""" type log-and-trap"""+"""
                          </configuration-set>"""
    
        cfg_req = ExecuteCfgCommandRequest(request_id=1, text_config=SET_SNMP_CONFIG, load_type=4,commit=ConfigCommit(commit_type=1))
        CONFIG_RESULT = mgd.ExecuteCfgCommand(cfg_req, timeout=60)
        
        print "Creating Route STUB"
        route_stub = Route.RibStub(channel)
        print "Creating a mqtt_client"
        mqtt_client = utility.openNotificationSession(device=R1)
        print  "Creating syslog topic to subscribe"
        syslog = utility.createSyslogTopic("SNMPD_RMON_EVENTLOG")
        print "Subscribing to Syslog RMON notifications"
        utility.subscribe(mqtt_client, syslog, on_message)
        while 1:
            1 + 1
    except AbortionError as ex:
        print ('The application got closed abruptly!!!')
        print ('Got exception: %s' % ex.message)
        print (traceback.print_exc())
        print (ex.code)
        print (ex.details)
    except Exception as ex:
        print (ex.message)
        print (traceback.print_exc())
    return

def _authenticateChannel(channel, user, passw, client_id):
    """
    This method authenticates the provided grpc channel.
    """
    sec_stub = authentication_service_pb2.LoginStub(channel)
    try:
        login_response = stub.LoginCheck(authentication_service_pb2.LoginRequest(user_name=user,password=password, client_id=request_id), timeout)
    except Exception as e:
        print('request id given is in use, using new one')
        res = sec_stub.LoginCheck(authentication_service_pb2.LoginRequest(user_name=username,password=user_password, client_id='id1'), timeout=60)
    return res


def _get_network_addr(addr_string):
    """
    Constructs a prpd_common_pb2.NetworkAddress object from the string
    :param addr_string: IPv4 string
    :return: return prpd_common_pb2.NetworkAddress 
    """
    ip = jnx_addr_pb2.IpAddress(addr_string=addr_string)
    return prpd_common_pb2.NetworkAddress(inet=ip)


def _get_route_match_fields(addr, table_name, prefix_len):
    """
    Constructs a Route.RouteMatchFields out of the given arguments
    :param addr:IPv4 address of the route
    :param table_name: Table that route belongs to
    :param prefix_len: Prefix len of route
    """
    netaddr = _get_network_addr(addr)
    rttablename = prpd_common_pb2.RouteTableName(name=table_name)
    routeTable = prpd_common_pb2.RouteTable(rtt_name=rttablename)
    return Route.RouteMatchFields(dest_prefix=netaddr,
                                  dest_prefix_len=prefix_len,
                                  table=routeTable)

def on_message(message):
    global route_present
    print("----------------------------------------EVENT RECEIVED-------------------------------------------")
    print "Event Type : " + message['jet-event']['event-id']

    if 'attributes' in message['jet-event'].keys():
        print "Event Attributes : ", message['jet-event']['attributes']['message']
    else:
        print "Attributes : NULL"
    print("-------------------------------------------------------------------------------------------------")

    p1 = re.search(r"Event " + re.escape(r1_interface_SNMP_INDEX) + r" triggered by Alarm 1, (\w+) threshold",
                   str(message['jet-event']['attributes']))
    res = p1.group(1)
    if (res == "rising") and (route_present is not True):
        print ("\n>>>>>>>>>>>>>>Primary Path input traffic rate is above threshold value<<<<<<<<<<<<<<<<<<<")
        routematchFields = _get_route_match_fields(route_prefix,
                                                   route_table_name,
                                                   32)
        routeAddr = _get_network_addr(NIP)
        gateway_list = [Route.RouteGateway(gateway_address=routeAddr)]
        nexthop_list = Route.RouteNexthop(gateways=gateway_list)

        route_entry = [Route.RouteEntry(key=routematchFields,
                                        nexthop=nexthop_list)]

        route_request = Route.RouteUpdateRequest(routes=route_entry)
        result = route_stub.RouteAdd(route_request, timeout=10)
       
        if result.status is Route.SUCCESS:
            route_present = True
            
            print "Added static route directly into control plane"
            print "Traffic to destination subnets routed via Secondary path"
            print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
            print '\n#############################Verifying RIB#######################################'
            routematchFields = _get_route_match_fields(route_prefix,
                                                       route_table_name,
                                                       0)
            rrequest = Route.RouteGetRequest(key=routematchFields)
            result = route_stub.RouteGet(rrequest, timeout=10)
            for single_res in result:
                for route in single_res.routes:
                    hops = route.nexthop
                    for nexthop_ip in hops.gateways:
                        print 'Next Hop Ips are:', nexthop_ip.gateway_address.inet.addr_string
                        if nexthop_ip.gateway_address.inet.addr_string == NIP:
                            print "Route add API injected route successfully"
            print '##################################################################################'
        else:
            print "V4RouteAdd service API activation failed \n"
            route_present = False
    elif (res == "falling") and (route_present is True):
        print ("\n>>>>>>>>>>>>>>Primary Path input traffic rate is below threshold value<<<<<<<<<<<<<<<<<<<")

        routematchFields = _get_route_match_fields(route_prefix,
                                                   route_table_name,
                                                   32)
        route_fields = [routematchFields]
        route_rem_req = Route.RouteRemoveRequest(keys=route_fields)
        result = route_stub.RouteRemove(route_rem_req, timeout=10)
        if result.status is Route.SUCCESS:
            route_present = False
            print "Primary path input traffic rate is below threshold, since deleted route"
            print "Entire Traffic routed back via Primary path"
            print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
        else:
            print "V4RouteDelete service API deactivation failed \n"
            route_present = True
    else:
        print "No changes required \n"


if __name__ == "__main__":
    main()


