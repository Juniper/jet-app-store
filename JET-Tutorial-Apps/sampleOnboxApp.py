"""
Copyright 2018-2022 Juniper Networks Inc.

This JET APP is for sample on-box execution demo 

Python3 compliant APP
"""

import argparse
import grpc

import authentication_service_pb2
import management_service_pb2


_HOST_OVERRIDE = 'host_name'

def Main():
    try:
        parser = argparse.ArgumentParser()

        parser.add_argument('-d','--device', help='Input hostname',
            required=True)
        parser.add_argument('-t','--timeout', help='Input time_out value',
            required=True,type=int)
        parser.add_argument('-u', '--user', help='Input username',
            required=True)
        parser.add_argument('-pw', '--password', help='Input password',
            required=True)

        args = parser.parse_args()

        #Establish grpc channel to jet router
        creds = grpc.ssl_channel_credentials((open('/tmp/RSA2048.pem').read()).encode('utf-8'),
                                                None, None)
        channel = grpc.secure_channel(args.device + ":32767", creds, 
            options=(('grpc.ssl_target_name_override', _HOST_OVERRIDE,),))

        #create stub for authentication services
        stub = authentication_service_pb2.LoginStub(channel)
        #Authenticate
        login_request = authentication_service_pb2.LoginRequest(
            user_name=args.user, password=args.password, client_id="SampleApp")
        login_response = stub.LoginCheck(login_request, args.timeout)

        #Check if authentication is successful
        if login_response.result == True:
            print("[INFO] Connected to gRPC Server:")
            print(login_response.result)
        else:
            print("[ERROR] gRPC Server Connection failed!!!")
            print(login_response.result)

        #Create stub for management services
        stub = management_service_pb2.ManagementRpcApiStub(channel)
        print("[INFO] Connected to JSD and created handle to mgd services")
        
        for i in range(1):
            #Provide API request details 
            op_xml_command = "<get-system-uptime-information>" \
            "</get-system-uptime-information>"
            op = management_service_pb2.ExecuteOpCommandRequest(
                xml_command=op_xml_command, out_format=2, request_id=1000)
            # Invoke API
            result = stub.ExecuteOpCommand(op, 100)
            # Check API response like status and output
            for i in result:
                print("[INFO] Invoked ExecuteOpCommand API return code = ")
                print(i.status)
                print("[INFO] Return output in CLI format = ")
                print(i.data)
    except Exception as ex:
        print(ex.message)

if __name__ == '__main__':
    Main()

