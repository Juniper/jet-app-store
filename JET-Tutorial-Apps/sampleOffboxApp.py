import argparse
import grpc

import authentication_service_pb2
import management_service_pb2
from management_service_pb2 import *

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
        creds = grpc.ssl_channel_credentials(open('/tmp/RSA2048.pem').read(),
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
            print "[INFO] Connected to gRPC Server:"
            print login_response.result
        else:
            print "[ERROR] gRPC Server Connection failed!!!"
            print login_response.result

        #Create stub for management services
        mgd_stub = management_service_pb2.ManagementRpcApiStub(channel)
        print "[INFO] Connected to JSD and created handle to mgd services"
        set_config = """<configuration-set>
                     set system location building bldg-name
                     set system location floor 4
                     </configuration-set>"""       
        cfg_req = ExecuteCfgCommandRequest(request_id=1, text_config=set_config, load_type=4,commit=ConfigCommit(commit_type=1))
        CONFIG_RESULT = mgd_stub.ExecuteCfgCommand(cfg_req, timeout=60)
        print "Configuration Status",CONFIG_RESULT 
     

    except Exception as ex:
        print ex

if __name__ == '__main__':
    Main()

