#Introduction [![Store Badge](https://img.shields.io/badge/JET-App-blue.svg)](https://github.com/Juniper/JetApp-Store)

JET application "TrafficManagement.py" listens to JET notifications. Whenever JET client receives monitored IFL
traffic rate rising threshold event, it pushes some of the prefixes traffic via redundant/backup link by programming router's control plane using jet RouteAdd API and delete routes in case of falling thresshold events.

Note: Before using the app, modify all variables like Router name, IFL, etc details.

# Topology

```
              R1                              R2
	   ______________                ______________
          |              |              |              |
          |              |              |              |
          |172.16.1.1/24 |---ge/0/0/0---|172.16.1.2/24 |
          |172.16.2.1/24 |---ge-0/0/1---|172.16.2.2/24 |
	  |______________|              |______________|
  
```
Pre-requisties:<br/>
1. IFL to be configured between router R1 and router R2<br/>
2. generate traffic from R2 to R1 ( for test purpose use ping command )<br/>
3. Install python 2.7.X in off-box(server, desktop, etc) and do `pip install -r requirements.txt` on that machine<br/>

##How to run App from On-box##

1. Copy TrafficManagement.py into R1 /var/db/scripts/jet/
2. Copy utility.py into R1 /var/db/scripts/jet/
3.  Configuration on R1<br/>
    set system scripts language python<br/>
    set system services extension-service request-response grpc clear-text address <router_management_ip/name> <br/>
    set system services extension-service notification allow-clients address <router_management_ip/name><br/>
    set system services netconf ssh 
    set interfaces ge-0/0/0 unit 0 family inet address 172.16.1.1/24
    set interfaces ge-0/0/1 unit 0 family inet address 172.16.2.1/24
    set interfaces lo0 unit 0 family inet address 192.168.10.1/32
    set interfaces lo0 unit 0 family inet address 127.0.0.1/32
    set protocols ospf area 0.0.0.0 interface all
    set protocols ospf area 0.0.0.0 interface fxp0.0 disable

4.  Configuration on R2<br/>
    set system services netconf ssh
    set interfaces ge-0/0/0 unit 0 family inet address 172.16.1.2/24
    set interfaces ge-0/0/1 unit 0 family inet address 172.16.2.2/24
    set interfaces lo0 unit 0 family inet address 192.168.20.1/32
    set interfaces lo0 unit 0 family inet address 127.0.0.1/32
    set protocols ospf area 0.0.0.0 interface all
    set protocols ospf area 0.0.0.0 interface fxp0.0 disable

5. Register your app on-box(R1) with the appropriate arguments value:
     (Below  mentioned args values are specifi to above topology ,connections and configuration specific. Make sure to change the argument values accurate one)

     set system extensions extension-service application file TrafficManagement.py arguments "-R1 <R1 ip > -username <user name> -user_password <password> -r1_interface ge-0/0/0.0 -grpc_port 32767 -NIP 172.16.2.2 -DIP 192.168.20.1/32 -CLIENT_ID 1234 -route_table_name inet.0 -route_prefix 192.168.20.1"

6. Run app from On-box
    `request extension-service start TrafficManagement.py`
    Note: to receive rising thershold events, do ping from R2 to R1 IFL IP with max size.
    
##How to run App from off-box##

1. Copy App into off-box 
2. Modify Router R1 name or ip ,destination IP, next-hop IP
3. Run app from Off-box
     (Below  mentioned args values are specifi to above topology ,connections and configuration specific. Make sure to change the argument values accurate one)

    python TrafficManagement.py -R1 <R1 ip > -username <user name> -user_password <password> -r1_interface ge-0/0/0.0 -grpc_port 32767 -NIP 172.16.2.2 -DIP 192.168.20.1/32 -CLIENT_ID 1234 -route_table_name inet.0 -route_prefix 192.168.20.1
    
    
###Sample Output###
```
user@R1-0> request extension-service stop TrafficManagement.py
Extension-service application 'TrafficManagement.py' with pid: 7129 exited with return: -1

user@R1-0> request extension-service start TrafficManagement.py
Extension-service application 'TrafficManagement.py' started with PID: 7179
Creating GRPC Channel
GRPC Channel Authentication check
request id given is in use, using new one
Authentication success
Creating Managment Srvice STUB
Invoked ExecuteOpCommand API return code =
0
SNMP_INDEX Value of monitoring IFL_interface:
ge-0/0/0.0
528
Configuring SNMP CONFIG
Creating Route STUB
Creating a mqtt_client
Creating syslog topic to subscribe
Subscribing to Syslog RMON notifications
----------------------------------------EVENT RECEIVED-------------------------------------------
Event Type : SNMPD_RMON_EVENTLOG
Event Attributes :
Event 528 triggered by Alarm 1, rising threshold (1024) crossed, (variable: ifIn1SecRate.528, value: 8288)
-------------------------------------------------------------------------------------------------

>>>>>>>>>>>>>>Primary Path input traffic rate is above threshold value<<<<<<<<<<<<<<<<<<<
Added static route directly into control plane
Traffic to destination subnets routed via Secondary path
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

#############################Verifying RIB#######################################
Next Hop Ips are:
172.16.2.2
Route add API injected route successfully
Next Hop Ips are:
172.16.1.2
Next Hop Ips are:
172.16.2.2
Route add API injected route successfully
##################################################################################
----------------------------------------EVENT RECEIVED-------------------------------------------
Event Type : SNMPD_RMON_EVENTLOG
Event Attributes :
Event 528 triggered by Alarm 1, falling threshold (1023) crossed, (variable: ifIn1SecRate.528, value: 0)
-------------------------------------------------------------------------------------------------

>>>>>>>>>>>>>>Primary Path input traffic rate is below threshold value<<<<<<<<<<<<<<<<<<<
Primary path input traffic rate is below threshold, since deleted route
Entire Traffic routed back via Primary path
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
^C[abort]

user@R1-0>

user@R2-1# run ping 192.168.10.1 source 172.16.1.2 size 1024

user@R1-0> show route 192.168.20.1

inet.0: 11 destinations, 12 routes (10 active, 0 holddown, 1 hidden)
+ = Active Route, - = Last Active, * = Both

192.168.20.1/32    *[Static/4] 00:01:11, metric2 0
                    > to 172.16.2.2 via ge-0/0/1.0
                    [OSPF/10] 00:52:30, metric 1
                      to 172.16.1.2 via ge-0/0/0.0
                    > to 172.16.2.2 via ge-0/0/1.0

user@R1-0> show route 192.168.20.1

inet.0: 11 destinations, 11 routes (10 active, 0 holddown, 1 hidden)
+ = Active Route, - = Last Active, * = Both

192.168.20.1/32    *[OSPF/10] 00:52:48, metric 1
                      to 172.16.1.2 via ge-0/0/0.0
                    > to 172.16.2.2 via ge-0/0/1.0
