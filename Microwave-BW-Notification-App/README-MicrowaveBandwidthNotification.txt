#Introduction [![Store Badge](https://img.shields.io/badge/JET-App-blue.svg)](https://github.com/Juniper/JetApp-Store)

"Microwave bandwidth notification" JET application receives notification whenever microwave signal streangth weakens then it discovers
remote router dynamically and modifies the mpls lsp bandwidth using JET APIs and deletes LSP bandwidth when microwave signal strentghens.

Note: Before using the app, modify all variables like Router name, ip, etc details

##Pre-requisites##

    1. Topology JNPR:R0----IPASO1-----IPASO2----JNPR:R1
    2. Enable routing between all above devices
    3. Configure ldp and mpls LSP (by name lsp1) between JNPR:R0 and JNPR:R1 devices
       set protocols mpls label-switched-path lsp1 from <JNPR:R0 IP>
       set protocols mpls label-switched-path lsp1 to <JNPR:R1 IP>
       set protocols mpls label-switched-path lsp1 primary r0
       set protocols mpls interface lo0.0
       set protocols ldp egress-policy ldp1
       set protocols ldp interface lo0.0
       set protocols ldp session <JNPR:R1 IP>
    
##Installation of the packages##

Download PySNMP packages from https://pypi.python.org/pypi/pysnmp/ and install juniper router's path /opt/lib/python2.7/ for
PySNMP to become operational:


    PyASN1, used for handling ASN.1 objects
    PySNMP, SNMP engine implementation

    Optional, but recommended:
    MIBs collection as PySNMP modules, to visualize more SNMP objects
    PySNMP-based command-line tools, can be used for quick testing and network management purposes 

    The installation procedure for all the above packages is as follows (on juniper router):
    
        $ tar zxf package-X.X.X.tar.gz
        $ cd package-X.X.X
        $ python setup.py install --prefix /opt/lib/python2.7/ install
        # rm -rf package-X.X.X
    If the above installation steps don't work you have to manually copy the packages to /opt/lib/python2.7/site-packages
    
Steps to configure and run the Bandwidth_management app:-

    1. copy bw_management_app.py app into juniper router where you need to receive the traps from IPASO
    2. Modify "openServerMode(('10.216.192.161', 162))" ip address with juniper jet router management IP.
    3. Run app "python bw_management_app.py"
    4. It will be listening for IPASO traps
    5. configure snmp trapreceiver as "juniper jet router" ip in IPASO device
    6. Modify link (between IPASO and Juniper device) bandwidth to >200 Mb
    7. App running in juniper router receives the trap from IPASO
    8. Find remote juniper router IP using mpls lsp stats
    9. Logs into remote juniper router and modifies lsp bandwidth to 200Mbps
    
How to run App from On-box:

1. Copy App into R0 /var/db/scripts/jet/MicrowaveBandwidthNotification.py
2. Configure above as jet script<br/>
    `set system scripts language python`<br/>
    `set system extensions extension-service application file MicrowaveBandwidthNotification.py`<br/>
3. Enable Jet in R0<br/>
    `set system services extension-service request-response grpc clear-text address <Router Management Ip>`<br/>
    `set system services extension-service request-response grpc max-connections 4`<br/>
    
4. Run app from On-box <br/>
    To run app in front-end<br/>
    `request extension-service start MicrowaveBandwidthNotification.py`<br/>
    To run app in background<br/>
    `set system extensions extension-service application file MicrowaveBandwidthNotification.py daemonize`<br/>
    `commit`<br/>
    `show extension-service status MicrowaveBandwidthNotification.py`<br/>
