Interduction:
--------------

This App will keep track of all the interfaces Carrier transition. if there is change found, it will notify the user on terminal and also sends syslog notification,
with the interface name and it's changed new value and old value of carrier transition. 

Note: Before using the app, modify all args values with the accurate one. here used some of the values are more generic/default.
 
Topology:
---------
              R0 
	   --------
          |        |              
          |        |
           --------   


##How to run App from On-box##

Configuration on R0:
    Copy Interface_Flap_Detection.py into R0's path /var/db/scripts/jet/
    and configure the router with below config:

    set system scripts language python<br/>
    set system services extension-service request-response grpc clear-text address <router_management_ip/name> <br/>
    set system services extension-service notification allow-clients address <router_management_ip/name><br/>
    set interfaces ge-0/0/0 unit 0 family inet address 10.1.1.1/24<br/>
    set system syslog file messages any any<br/>
    set system syslog file messages archive files 1<br/> 

Register your app on-box:
    set system extensions extension-service application file Interface_Flap_Detection.py arguments "-device <router_management_ip/name> -user <username> -password <password> -request_id 100 -grpc_port 32767"
       
Run app from On-box
    `request extension-service start Interface_Flap_Detection.py`

 Run app from Off-box
     'python Interface_Flap_Detection.py arguments -device <router_management_ip/name> -user <username> -password <password> -request_id 100 -grpc_port 32767'


note : To Recevie the notification disable one of the R1 Interface.

Sample out-put:
----------------
user@R1# run request extension-service start Interface_Flap_Detection.py
Extension-service application 'Interface_Flap_Detection.py' started with PID: 8050
Creating GRPC Channel
GRPC Channel Authentication check
request id given is in use, using new one
Authentication success
Creating Managment Srvice STUB
Interface Flap Detection Starting
---------------------------------------LISTENING FOR INTERFACE_FLAP--------------------------------------------
----------------------------------------INTERFACE FLAP EVENT RECEIVED-------------------------------------------
Interface-flap-notification: for interface ge-0/0/0 flap count increased from 5 to 6
('syslog notification status', 0)
----------------------------------------INTERFACE FLAP EVENT RECEIVED-------------------------------------------
Interface-flap-notification: for interface ge-0/0/0 flap count increased from 6 to 7
('syslog notification status', 0)
^C[abort]

-------
[edit]
user@R1#

user@R1# set disable

[edit interfaces ge-0/0/0]
user@R1# commit
commit complete

[edit interfaces ge-0/0/0]
user@R1# delete disable

[edit interfaces ge-0/0/0]
user@R1# commit
commit complete

[edit interfaces ge-0/0/0]
user@R1#

Syslog notification:
-------------------
user@R1# run show log messages | grep "R1 logger"
Sep 21 11:30:16  R1 logger: Interface-flap-notification: for interface ge-0/0/0 flap count increased from 5 to 6
Sep 21 11:30:22  R1 logger: Interface-flap-notification: for interface ge-0/0/0 flap count increased from 6 to 7

