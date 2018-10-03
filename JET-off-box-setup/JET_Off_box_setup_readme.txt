NOTE: All the JET apps in the main repositories are validated on 17.4R1

Fallow the below steps to setup the off-box(Ubuntu or Linux or any host machines) for JET app off-box execution

1) Install the below mentioned packages on off-box:
Python2.7
grpcio==1.0.4
grpcio-tools==1.0.4

2) Download the JET IDL from the juniper website” https://support.juniper.net/support/downloads/”
And unpack:
E.g.:
user@ubuntu:~/JET_IDL$ ls
jet-idl-17.4R1-S2.2.tar.gz
jcluser@jet-vm:~/JET_IDL$ tar -zxvf jet-idl-17.4R1-S2.2.tar.gz
proto
proto/jnx_base_types.proto
proto/jnx_addr.proto
proto/firewall_service.proto
proto/dcd_service.proto
proto/cos_service.proto
proto/authentication_service.proto
proto/bgp_route_service.proto
proto/prpd_common.proto
proto/mpls_api_service.proto
proto/management_service.proto
proto/registration_service.proto
proto/prpd_service.proto
proto/rib_service.proto
proto/routing_interface_service.proto
jcluser@jet-vm:~/JET_IDL$ ls
jet-idl-17.4R1-S2.2.tar.gz  proto
user@ubuntu:~/JET_IDL$

3) Compile python and grpc modules for required Service proto files as below:
user@ubuntu:~/JET_IDL$ python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. proto/*.proto
user@ubuntu:~/JET_IDL$ ls *.py
authentication_service_pb2_grpc.py  jnx_addr_pb2_grpc.py            prpd_service_pb2_grpc.py
authentication_service_pb2.py       jnx_addr_pb2.py                 prpd_service_pb2.py
bgp_route_service_pb2_grpc.py       jnx_base_types_pb2_grpc.py      registration_service_pb2_grpc.py
bgp_route_service_pb2.py            jnx_base_types_pb2.py           registration_service_pb2.py
cos_service_pb2_grpc.py             management_service_pb2_grpc.py  rib_service_pb2_grpc.py
cos_service_pb2.py                  management_service_pb2.py       rib_service_pb2.py
dcd_service_pb2_grpc.py             mpls_api_service_pb2_grpc.py    routing_interface_service_pb2_grpc.py
dcd_service_pb2.py                  mpls_api_service_pb2.py         routing_interface_service_pb2.py
firewall_service_pb2_grpc.py        prpd_common_pb2_grpc.py
firewall_service_pb2.py             prpd_common_pb2.py
user@ubuntu:~/JET_IDL$
Copy the required python files to the “/usr/lib/python2.7/dist-packages/” or “/usr/lib/python2.7/site-packages/”

4) To start executing the JET app’s off-box, fallow the off-box execution steps from the readme file of respective JET-APP.

