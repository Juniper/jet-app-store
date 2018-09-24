#Introduction [![Jet App Badge](https://img.shields.io/badge/JET-App-blue.svg)](https://github.com/Juniper/JetApp-Store)

This Dynamic COS App monitors satellite site's modems in 10 seconds interval and detects the changes in modem codes, error noise ratios
and symbol rates. Then computes new COS values based on changes in modem values and generate cos configurations and dynamically pushes
to site's ingess interface of MX based Edge router and also updates dynamic server db with new values.

Note: Before using the app, modify all variables like Router name, site ip, etc details

### Topology

```   
    R0-----R1
    |       |
   ----SW----
  /  |   |   \
 S1  S2  S3  S4
```
# Pre-requisties
1. R0 and R1 to configured with intergess and egress interface configurations and COS
2. There are two option to poll the site's modems one is using NMS server or load PySNMP in router and configure SNMP server to poll the MODEMS 
3. Install python 2.7.X in off-box(server, desktop, etc) and python grpc module in case app is to be executed from Off-box
4. One needs to install dependencies given in requirements.txt via `pip install -r requirements.txt`
5. For on-box deployment, download PySNMP packages from https://pypi.python.org/pypi/pysnmp/ and install in juniper router's path /opt/lib/python2.7/.
    For PySNMP to become operational we require:

        1. PyASN1, used for handling ASN.1 objects
        2. PySNMP, SNMP engine implementation
        3. PySMI
        
6. Optional, but recommended:
   
   MIBs collection as PySNMP modules, to visualize more SNMP objects
   PySNMP-based command-line tools, can be used for quick testing and network management purposes 

The installation procedure for all the above packages is as follows (on juniper router):
```bash
    $ tar zxf package-X.X.X.tar.gz
    $ cd package-X.X.X
    $ cp -r <packge-name> /opt/lib/python2.7/site-packages
```
### Generating ssl certificate for grpc
1. On your machine run

    `openssl req -x509 -nodes -days 365 -newkey rsa:1024 -keyout cert.pem -out cert.pem`
2. NOTE: Enter the domain name of your router in the "Common name" field for certificate
3. Copy this certificate to /var/tmp location of the router whose domain name you specified in Common name of certificate
4. Run `set security certificates local r2st load-key-file /var/tmp/cert.pem` in config mode and commit

### How to run and deploy App On-box

1. Copy App( DynamicCOS.py ) and input.yaml file and generated certificates for routers into R0 /var/db/scripts/jet<br/>
2. Certificate name should follow this convention: `<router_name>.pem`
2. Configure the app as jet script<br/>
    `set system scripts language python`<br/>
    `set system extensions extension-service application file DynamicCOS.py` <br/>
3. Enable Jet in R0<br/>
   `set system services extension-service request-response grpc ssl local-certificate cert`<br/>
   `set system services extension-service request-response grpc max-connections 4`<br/>

4. Run app from On-box<br/>
    To run app in front-end<br/>
    `request extension-service start DynamicCOS.py`<br/>
    To run app in background<br/>
    `set system extensions extension-service application file DynamicCOS.py daemonize`<br/>
    `commit`<br/>
    `show extension-service status DynamicCOS.py`<br/>

### How to run and deploy App off-box

1. Copy App into off-box
2. Modify Router R0 IP address, interface index, destination IP, next-hop IP in input.yml
3. Generate and place the certificates in the app directory. Follow this convention: `<router_name>.pem`
3. Run app from Off-box
    
    `python DynamicCOS.py`

## Sample Output

```
Authentication success for S1
Authentication success for S2
Authentication success for S3
Authentication success for S4
Authentication success for R1
Authentication success for R2
Pushing firewall filter configuration using JET FW AccessListAdd API
Bind filter configuration template
Bind filter to physical interface using JET AccessListBindAdd
Site_S1 Initial COS configuration activation in Router_R1 is successful
Pushing firewall filter configuration using JET FW AccessListAdd API
Bind filter configuration template
Bind filter to physical interface using JET AccessListBindAdd
Site_S2 Initial COS configuration activation in Router_R1 is successful
Pushing firewall filter configuration using JET FW AccessListAdd API
Bind filter configuration template
Bind filter to physical interface using JET AccessListBindAdd
Site_S3 Initial COS configuration activation in Router_R1 is successful
Pushing firewall filter configuration using JET FW AccessListAdd API
Bind filter configuration template
Bind filter to physical interface using JET AccessListBindAdd
Site_S4 Initial COS configuration activation in Router_R1 is successful
Pushing firewall filter configuration using JET FW AccessListAdd API
Bind filter configuration template
Bind filter to physical interface using JET AccessListBindAdd
Site_S1 Initial COS configuration activation in Router_R2 is successful
Pushing firewall filter configuration using JET FW AccessListAdd API
Bind filter configuration template
Bind filter to physical interface using JET AccessListBindAdd
Site_S2 Initial COS configuration activation in Router_R2 is successful
Pushing firewall filter configuration using JET FW AccessListAdd API
Bind filter configuration template
Bind filter to physical interface using JET AccessListBindAdd
Site_S3 Initial COS configuration activation in Router_R2 is successful
Pushing firewall filter configuration using JET FW AccessListAdd API
Bind filter configuration template
Bind filter to physical interface using JET AccessListBindAdd
Site_S4 Initial COS configuration activation in Router_R2 is successful
##################SITE-S1 POLLED DATA& ACTIONS################
SITE-S1 IP: 192.168.10.1
SITE-S1 TYPE: 1
SITE-S1 MODCOD: 16
Modified CIR Value: 158.76072
Modified PIR Value: 238.14108
Modify policer with new CIR values using JET APIS
Pushing policer changes using JET AccessListPolicerReplace API
Modified policer CIR in Router R1 with new value: 158.76072
Modified policer CIR changes are effective
Modify policer with new CIR values using JET APIS
Pushing policer changes using JET AccessListPolicerReplace API
Modified policer CIR in Router R2 with new value: 158.76072
Modified policer CIR changes are effective
###################END OF ACTIONS ON SITE-1##################

##################SITE-S2 POLLED DATA& ACTIONS################
SITE-S2 IP: 192.168.20.2
SITE-S2 TYPE: 1
SITE-S2 MODCOD: 19
Modified CIR Value: 124.602576
Modified PIR Value: 186.903864
Modify policer with new CIR values using JET APIS
Pushing policer changes using JET AccessListPolicerReplace API
Modified policer CIR in Router R1 with new value: 124.602576
Modified policer CIR changes are effective
Modify policer with new CIR values using JET APIS
Pushing policer changes using JET AccessListPolicerReplace API
Modified policer CIR in Router R2 with new value: 124.602576
Modified policer CIR changes are effective
###################END OF ACTIONS ON SITE-2##################

##################SITE-S3 POLLED DATA& ACTIONS################
SITE-S3 IP: 192.168.30.3
SITE-S3 TYPE: 2
SITE-S3 MODCOD: 4
Modified CIR Value: 29.66574
Modified PIR Value: 44.49861
Modify policer with new CIR values using JET APIS
Pushing policer changes using JET AccessListPolicerReplace API
Modified policer CIR in Router R1 with new value: 29.66574
Modified policer CIR changes are effective
Modify policer with new CIR values using JET APIS
Pushing policer changes using JET AccessListPolicerReplace API
Modified policer CIR in Router R2 with new value: 29.66574
Modified policer CIR changes are effective
###################END OF ACTIONS ON SITE-3##################

##################SITE-S4 POLLED DATA& ACTIONS################
SITE-S4 IP: 192.168.40.4
SITE-S4 TYPE: 2
SITE-S4 MODCOD: 20
Modified CIR Value: 44.318722
Modified PIR Value: 66.478083
Modify policer with new CIR values using JET APIS
Pushing policer changes using JET AccessListPolicerReplace API
Modified policer CIR in Router R1 with new value: 44.318722
Modified policer CIR changes are effective
Modify policer with new CIR values using JET APIS
Pushing policer changes using JET AccessListPolicerReplace API
Modified policer CIR in Router R2 with new value: 44.318722
Modified policer CIR changes are effective
###################END OF ACTIONS ON SITE-4##################

!!!!!!!!!Sleeping for 10 Sec polling interval!!!!!!!!!!!!!!!
##################SITE-S1 POLLED DATA& ACTIONS################
SITE-S1 IP: 192.168.10.1
SITE-S1 TYPE: 1
SITE-S1 MODCOD: 16
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-1##################

##################SITE-S2 POLLED DATA& ACTIONS################
SITE-S2 IP: 192.168.20.2
SITE-S2 TYPE: 1
SITE-S2 MODCOD: 19
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-2##################

##################SITE-S3 POLLED DATA& ACTIONS################
SITE-S3 IP: 192.168.30.3
SITE-S3 TYPE: 2
SITE-S3 MODCOD: 4
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-3##################

##################SITE-S4 POLLED DATA& ACTIONS################
SITE-S4 IP: 192.168.40.4
SITE-S4 TYPE: 2
SITE-S4 MODCOD: 20
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-4##################

!!!!!!!!!Sleeping for 10 Sec polling interval!!!!!!!!!!!!!!!
```
