"""
Copyright 2018 Juniper Networks Inc.

This JET APP will get the device information

"""

#!/usr/bin/env python
#
# Import Python GRPC module
from grpc.beta import implementations

# Import python modules generated from proto files
import mgd_service_pb2
import authentication_service_pb2

# IMPORTANT: Following are the dummy parameters that will be used for testing
# Please change these parameters for proper testing

# Device details and login credentials
JSD_IP = 'your.device.ip'     # Update with your device name/IP
JSD_PORT = 32767
USERNAME = 'username'       # Update with your device login details
PASSWORD = 'password'       # Update with your device login details
CLIENT_ID = 'sampleoffboxapp'
_TIMEOUT_SECONDS = 20


def EstablishChannel(address, port, client_id, user, password):
    # Open a grpc channel to the device
    creds = implementations.ssl_channel_credentials(open('/tmp/host.pem').read(), None, None)
    channel = implementations.secure_channel(address, port, creds)

    # Create stub for authentication
    login_stub = authentication_service_pb2.beta_create_Login_stub(channel)

    # Fill the login request message structure
    login_request = authentication_service_pb2.LoginRequest(user_name=user, password=password, client_id=client_id)

    # Invoke the login check API
    login_response = login_stub.LoginCheck(login_request, _TIMEOUT_SECONDS)
    print login_response

    return channel

def ManagementTests(channel):

    # Create a stub for Management RPC
    stub = mgd_service_pb2.beta_create_ManagementRpcApi_stub(channel)

    set_config = """<configuration-set>
                     set system location building bldg-name
                     set system location floor 4
                     </configuration-set>"""

    # Execute ExecuteOpCommand RPC
    executeCfgCommandrequest = mgd_service_pb2.ExecuteCfgCommandRequest(text_config = set_config,
								 request_id = 1000, load_type=mgd_service_pb2.CONFIG_LOAD_SET,
                                 commit=mgd_service_pb2.ConfigCommit(commit_type=1))

    response = stub.ExecuteCfgCommand(executeCfgCommandrequest, _TIMEOUT_SECONDS)
    print response


def Main():

    #Establish a connection and authenticate the channel
    channel = EstablishChannel(JSD_IP, JSD_PORT, CLIENT_ID, USERNAME, PASSWORD)

    # Call sample operational command
    ManagementTests(channel)

if __name__ == '__main__':
    Main()
