#!/usr/bin/env python
import re
import traceback
import argparse
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
#device = 'router'
#user = 'user' 
#password = 'user_pwd'
#grpc_port ='32767'
#request_id = '31231'

flag1 = 1
flag =1


def main():
    try:
        global  mgd, device, user, password, grpc_port, request_id 
        parser = argparse.ArgumentParser()
        parser.add_argument('-device',help="Hostname or ip ",type=str )
        parser.add_argument('-user', help="host Username",type=str)
        parser.add_argument('-password', help="password for the host user",type=str)
        parser.add_argument('-grpc_port', help="GRPC port number",type=str)
        parser.add_argument('-request_id', help="client id",type=str)
        args, unknown = parser.parse_known_args()
    
        device = args.device or device
        user = args.user or user
        password = args.password or password
        grpc_port = args.grpc_port or grpc_port
        request_id = args.request_id or request_id
    
        print "Creating GRPC Channel"
        channel = grpc.insecure_channel(device+':'+grpc_port)
        print "GRPC Channel Authentication check"
        res = _authenticateChannel(channel, user, password, request_id)
        print "Authentication "+('success' if res else 'failure')
        if res is False:
            return

        print "Creating Managment Srvice STUB"
        mgd = management_service_pb2.ManagementRpcApiStub(channel)
        print "Interface Flap Detection Starting"
        flag0=1
        while flag0:
            Interface_Flap_Detection() 
    except AbortionError as ex:
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
        res = sec_stub.LoginCheck(authentication_service_pb2.LoginRequest(user_name=user,password=password, client_id='request'), timeout=60)
    return res

def Interface_Flap_Detection():
    """
    this module will keep track of interface Carrier transition changes and generate the syslog notification for the same.
    """
    global flag1, flag, reference_interface_list
    op_command = "show interfaces extensive"
    op = ExecuteOpCommandRequest(cli_command = op_command, out_format = 2, request_id = 1000)
    result = mgd.ExecuteOpCommand(op,timeout=60)
    response = ""
    for i in result:
        response += i.data
    all_interfaces=re.findall(r'Physical interface:\s+\w+-\d+/\d+/\d+,\s.*Carrier transitions:\s\d+',response,re.DOTALL)
    all_interfaces = ''.join(all_interfaces)
    monitoring_interface = {}
    interface_list = all_interfaces.split('interface:')
    for key in interface_list:
       interface_match=re.search(r'(\w+-\d+\/\d+\/\d+).*Carrier transitions.*?: (\d+)',key,re.DOTALL)
       if interface_match:
           monitoring_interface[interface_match.group(1)]=interface_match.group(2)

    while flag1:
        reference_interface_list = monitoring_interface
        flag1=0
    for i in monitoring_interface.keys():
        if i not in reference_interface_list.keys():
            reference_interface_list[i] = monitoring_interface[i]

    for i in monitoring_interface.keys():
        if(int(monitoring_interface[i])-int(reference_interface_list[i])>=1):
            print("----------------------------------------INTERFACE FLAP EVENT RECEIVED-------------------------------------------")
            str1="Interface-flap-notification: "+"for interface "+i+" flap count increased from "+reference_interface_list[i]+" to "+monitoring_interface[i]
            print(str1)
            str="logger -e Interface-flap-notification "+"for interface "+i+" flap count increased from "+reference_interface_list[i]+" to "+monitoring_interface[i]
            op_command = "request routing-engine execute command "+"\""+str+"\""
            op = mgd.ExecuteOpCommand(ExecuteOpCommandRequest(cli_command = op_command, out_format = 2, request_id =1000),timeout=60)
            for j in op:
                print("syslog notification status",j.status)
            reference_interface_list[i] = monitoring_interface[i]

        else:
            while flag:
                print("---------------------------------------LISTENING FOR INTERFACE_FLAP--------------------------------------------")
                flag=0

if __name__ == "__main__":
    main()

