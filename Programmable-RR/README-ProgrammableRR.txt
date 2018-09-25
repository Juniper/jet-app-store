App Description:
================

"ProgrammableRR.py" is an on-box JET App that uses the BGP APIs to program routes in the Route Reflector. Route Operations supported by this App are Route Addition, Modification, Deletion and Get (route query). Route operation requests are sent to this App in JSON format from the client scripts which can reside in any server. BGP routes added by this App through the BGP APIs will be installed as protocol type "BGP-Static".


1.) App creates a TCP socket, binds it to a port 8888 and starts to listen for the incoming connection on the socket to receive route operation requests from the client scripts. 

2.) Client scripts establishes a TCP socket connection to the port 8888 opened by the on-box app and sends route operation requests (Route Addition/Modification/Deletion/GET) in the JSON format.

3.) On-Box App receives JSON request, determines the route operation from the "action" keyword in the JSON to be either add/modify/delete/query operation and then calls the appropriate BGP APIs to perform the tasks.

4.) In the case of Route GET operation, client script sends JSON request to query all the programmed routes. On-Box App encodes the obtained route information from BGP in the JSON format and sends to the client script.


Client scripts used for this App are:

RouteAdd-Client.py
RouteModify-Client.py
RouteDelete-Client.py
RouteGet-Client.py


Topology:
==========
                                  [BGP RR]                 [RR Client]

Client Script  --------------->      R0      ------------>    R1

                               (On-Box JET APP)
                                

How to run App from On-box:
===========================


1. Edit the JET App "ProgrammableRR.py" to fill the following fields in it. HOST is preferabbly the management (fxp0) address or Loopback address of RR.
USER/PASSWORD are the login credentials of the RR.

#Variables for THRIFT/MQTT connection
HOST = 'IP of Router'
USER = 'lab'
PASSWORD = 'lab'


2. Copy JET App "ProgrammableRR.py" to the RR (R0 router) at the following location:
    
    /var/db/scripts/jet/


3. Enable JET in R0:

    set system scripts language python
    set system services extension-service request-response thrift clear-text
    set system services extension-service request-response thrift max-connections 4
    set system services extension-service notification allow-clients address 0.0.0.0/0
    set interfaces lo0 unit 0 family inet address 127.0.0.1/32


4. Configure the App as JET file. The optional 'Daemonize' knob will run the App in background as daemon immediately after this config is committed.
    
    set system scripts jet file ProgrammableRR.py daemonize


5. Alternately App can be started/stoped as below if the 'daemonize' knob is not used.
    
    request extension-service start ProgrammableRR.py    
    request extension-service stop ProgrammableRR.py    





Sample Output of Route Operation by the App:
=============================================


## Start the App on the RR (R0 Router)

Router> request extension-service start ProgrammableRR.py    
Extension-service application 'ProgrammableRR.py' started with PID: 12946



#### Start Route Operation through Client Scripts  ####

-bash-4.2# uname -a
Linux nms5-vm-linux2 3.11.10-100.fc18.x86_64 #1 SMP Mon Dec 2 20:28:38 UTC 2013 x86_64 x86_64 x86_64 GNU/Linux
-bash-4.2# 


## Route Add operation
-bash-4.2# python RouteAdd-Client.py
Preparing Route Information JSON Object
[{'ipv4address': '192.168.10.1/32', 'action': 'add', 'next_hop': '172.16.1.1', 'community': '100:101'}]
Route Information Sent on socket, total bytes =  110

[{"returncode": "0"}]
Closing Socket
-bash-4.2# 


## Route Modify operation: Modifies the Next-Hop of the already installed route.
-bash-4.2# python RouteModify-Client.py
Preparing Route Information JSON Object
[{'ipv4address': '192.168.10.1/32', 'action': 'modify', 'next_hop': '172.16.2.1', 'community': '100:101'}]
Route Information Sent on socket, total bytes =  113

[{"returncode": "0"}]
Closing Socket
-bash-4.2#


## Route GET operation: Queries the programmed routes on the box
-bash-4.2# python RouteGet-Client.py
Creating Route Information JSON Object
Route Query Sent to the JET app:  [{'action': 'query', 'prefix': 'all'}]
[{'ipv4address':'192.168.10.1', 'next_hop':'172.16.2.1', 'community':'100:101' }]
Total routes received =  1
Closing Socket
-bash-4.2# 


## Route Delete operation: Deletes the already installed route.
-bash-4.2# python RouteDelete-Client.py
Preparing Route Information JSON Object
[{'ipv4address': '192.168.10.1/32', 'action': 'delete'}]
Route Information Sent on socket, total bytes =  64

[{"returncode": "0"}]
Closing Socket
-bash-4.2# 


