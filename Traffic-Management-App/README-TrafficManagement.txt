Introduction

JET application "TrafficManagement.py" listnes to JET notifications. Whenever JET client receives monitored IFL
traffic rate rising threshold event, it pushes some of the prefixes traffic via redundant/backup link by programming router's
control plane using jet RouteAdd API and delete routes in case of falling thresshold events.

Note: Before using the app, modify all variables like Router name, IFL, etc details

Topology:

R0-------------------------------R1
(IFL ge-0/0/0.0)        10.1.1.2/24
     IP-10.1.1.1/24
Pre-requisties:

1. IFL to be configured between router RO and router R1
2. generate traffic from R1 to R0
3. Install python 2.7.X in off-box(server, desktop, etc) and Jet client package in case App to be executed from Off-box

How to run App from On-box:

1. Copy App into R0 /var/db/scripts/jet/App.py
2. Configure above as jet script
    set system scripts jet file App.py
3. Enable Jet in R0
    set system services extension-service thrift request-response clear-text address <router management IP/Name>
    set system services extension-service thrift request-response max-connection 8
    set system services extension-service notification-server address <router management IP/Name>
4. Configure RMON to monitor IFL traffic rate threshold events
    set snmp rmon alarm 1 interval 1
    set snmp rmon alarm 1 variable ifIn1SecRate.541
    set snmp rmon alarm 1 sample-type absolute-value
    set snmp rmon alarm 1 request-type get-request
    set snmp rmon alarm 1 rising-threshold 1024
    set snmp rmon alarm 1 falling-threshold 1023
    set snmp rmon alarm 1 rising-event-index 541
    set snmp rmon alarm 1 falling-event-index 541
    set snmp rmon alarm 1 syslog-subtag IFINDEX541
    set snmp rmon event 541 type log-and-trap
    Note: replace 541 with actual IFL snmp index id in above config
5. Run app from On-box
    jet TrafficManagement.py
    Note: to receive rising thershold events, do ping from R1 on R0 IFL IP with max size.
How to run App from off-box:

1. Copy App into off-box
2. Modify Router R0 name, interface index, destination IP, next-hop IP
3. Run app from Off-box
    python TrafficManagement.py
    
    
Sample Output:

c:\JET\UC\Scripts>python TrafficManagement.py
Connecting to server

Established connection with the r0nec
Notification client connected
------------------------------------------------------------------------
Rising threshold
IFL input traffic rate is above threshold, hence added route

------------------------------------------------------------------------
Falling threshold
IFL input traffic rate is below threshold, hence deleting route

------------------------------------------------------------------------
Falling threshold
No configuration changes required


regress@r0nec> show route 1.1.1.1    

inet.0: 34 destinations, 34 routes (33 active, 0 holddown, 1 hidden)
+ = Active Route, - = Last Active, * = Both

1.1.1.1/32         *[Static/5] 00:00:19, metric2 0
                    > to 10.216.223.254 via fxp0.0