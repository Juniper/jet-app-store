"""
Copyright 2018 Juniper Networks Inc.

This JET APP is for getting the os version of JET server
"""

#!/usr/bin/env python
import argparse
import grpc
import traceback
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


#device = 'r1_ip'
#user = 'user'
#password = 'user_pwd'
#grpc_port = '32767' 
#request_id = '1234'
timeout= 60
def Main():
    try:
        global device, user, password, grpc_port,request_id
        parser = argparse.ArgumentParser()
        parser.add_argument('-device', help='Input host name or ip ', type=str)
        parser.add_argument('-user', help='Input username for host', type=str)
        parser.add_argument('-password', help='Input password for host', type=str)
        parser.add_argument('-grpc_port', help='Input grpc port',type=str)
        parser.add_argument('-request_id', help='Input client request id',type=str)
        args, unknown = parser.parse_known_args()
        
        device = args.device or device
        user =  args.user or user
        password = args.password or password
        grpc_port = args.grpc_port or grpc_port
        request_id = args.request_id or request_id

        channel = grpc.insecure_channel(device+':'+grpc_port)
        stub = authentication_service_pb2.LoginStub(channel)
        try: 
            login_response = stub.LoginCheck(authentication_service_pb2.LoginRequest(user_name=user,password=password, client_id=request_id), timeout)
        except Exception as e:
            print('request id given is in use, using new one')  
            login_response = stub.LoginCheck(authentication_service_pb2.LoginRequest(user_name=user,password=password, client_id='new'), timeout) 

        if login_response.result :
            print "[INFO] Connected to gRPC Server:",+login_response.result
        else:
            print "[ERROR] gRPC Server Connection failed!!!",+login_response.result

        mgd = management_service_pb2.ManagementRpcApiStub(channel)

        op_command = "show version"
        op = ExecuteOpCommandRequest(cli_command = op_command, out_format = 2, request_id = 1000)
        result = mgd.ExecuteOpCommand(op, timeout)
        response ='' 
        for i in result:
            response += i.data
        if i.status == 0:
            print 'Invoked ExecuteOpCommand API return code = ', i.status
            print 'Invoked ExecuteOpCommand API return code = ', i.data 
        else:
            print 'Something Went Wrong !!! Data not received'
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

if __name__ == '__main__':
    Main()



