Introduction

JET application "ProgrammableRR.py" listens to the JSON requests from the Provisioning Server and programs the routes in the RR.



Topology:


PS ------------> R0 -----------R1



How to run App from On-box:

1. Copy App into R0 /var/db/scripts/jet/ProgrammableRR.py
2. Configure above as jet script. Daemonize knob will run the App in background as daemon.
    set system scripts jet file ProgrammableRR.py daemonize
3. Enable Jet in R0
    set system services extension-service thrift request-response clear-text address <router management IP/Name>
    set system services extension-service thrift request-response max-connection 8
    set system services extension-service notification-server address <router management IP/Name>

How to run App from off-box:

1. Copy App into off-box
2. Run app from Off-box
    python ProgrammableRR.py
    
    
Sample Output of programmed route:

Router> show route 101.1.1.1/32 extensive 

inet.0: 2068 destinations, 2068 routes (2068 active, 0 holddown, 0 hidden)
Restart Complete
101.1.1.1/32 (1 entry, 1 announced)
        State: <FlashAll>
        *BGP-Static Preference: 5/-101
                Next hop type: Indirect, Next hop index: 0
                Address: 0x6615150
                Next-hop reference count: 1
                Protocol next hop: 1001:1:1:1::1
                Indirect next hop: 0x2 no-forward INH Session ID: 0x0
                State: <Active Int Ext AlwaysFlash NSR-incapable Programmed>
                Age: 7:28:51 	Metric2: 0 
                Validation State: unverified 
                Announcement bits (2): 4-LDP 6-Resolve tree 2 
                AS path: I
                Communities: encapsulation:v4ov6(14)
                Indirect next hops: 1
                        Protocol next hop: 1001:1:1:1::1
                        Indirect next hop: 0x2 no-forward INH Session ID: 0x0
                        Indirect path forwarding next hops: 1
                                Next hop type: Router
                                Next hop: 2001:30:30:30:1::1 via xe-2/0/1.0
                                Session Id: 0x0
			::/0 Originating RIB: inet6.0
			  Node path count: 1
			  Forwarding nexthops: 1
				Nexthop: 2001:30:30:30:1::1 via xe-2/0/1.0

Router> 


