Introduction

This Dynamic COS App monitors satellite site's modems in 10 seconds interval and detects the changes in modem codes, error noise ratios
and symbol rates. Then computes new COS values based on changes in modem values and generate cos configurations and dynamically pushes
to site's ingess interface of MX based Edge router and also updates dynamic server db with new values.

Note: Before using the app, modify all variables like Router name, site ip, etc details

Topology:

    R0-----R1
    |       |
   ----SW----
  /  |   |   \
 S1  S2  S3  S4
 
Pre-requisties:
1. R0 and R1 to configured with intergess and egress interface configurations and COS
2. There are two option to poll the site's modems one is using NMS server or load PySNMP in router and configure SNMP server to poll the MODEMS 
3. Install python 2.7.X in off-box(server, desktop, etc) and Jet client package in case App to be executed from Off-box

How to run App from On-box:

1. Copy App and input.yaml file into R0 /var/db/scripts/jet/DynamicCOS.py
2. Configure above as jet script
    set system scripts language python
    set system extensions extension-service application file DynamicCOS.py 
3. Enable Jet in R0
    set system services extension-service request-response thrift clear-text address Router Management IP
    set system services extension-service request-response thrift clear-text port 9090
    
4. Run app from On-box
    To run app in front-end
    request extension-service start DynamicCOS.py
    To run app in background
    set system extensions extension-service application file DynamicCOS.py daemonize
    commit
    show extension-service status DynamicCOS.py

How to run App from off-box:

1. Copy App into off-box
2. Modify Router R0 IP address, interface index, destination IP, next-hop IP
3. Run app from Off-box
    python DynamicCOS.py


Sample Output:

/Library/Frameworks/Python.framework/Versions/2.7/bin/python2.7 /Users/gvenkata/Documents/juniper/CEs/DynamicCOS.py
client authentication successful to Site: S1
client authentication successful to Site: S2
client authentication successful to Site: S3
client authentication successful to Site: S4
client authentication successful to Site: R1
client authentication successful to Site: R2
Site_S1 Initial fw configuration activation is successful
Site_S2 Initial fw configuration activation is successful
Site_S3 Initial fw configuration activation is successful
Site_S4 Initial fw configuration activation is successful
Site_S1 Initial fw configuration activation is successful
Site_S2 Initial fw configuration activation is successful
Site_S3 Initial fw configuration activation is successful
Site_S4 Initial fw configuration activation is successful
##################SITE-S1 POLLED DATA& ACTIONS################
SITE-S1 IP: 1.1.1.1
SITE-S1 TYPE: 1
SITE-S1 MODCOD: 16
Modified CIR Value: 158.76072
Modified PIR Value: 238.14108
Modified S1 policer CIR in Router R1 with new value: 158.76072
Modified S1 policer CIR changes are effective
Modified S2 policer CIR in Router R2 with new value: 158.76072
Modified S2 policer CIR changes are effective
###################END OF ACTIONS ON SITE-S1##################
##################SITE-S2 POLLED DATA& ACTIONS################
SITE-S2 IP: 2.2.2.2
SITE-S2 TYPE: 1
SITE-S2 MODCOD: 19
Modified CIR Value: 124.602576
Modified PIR Value: 186.903864
Modified S1 policer CIR in Router R1 with new value: 124.602576
Modified S1 policer CIR changes are effective
Modified S2 policer CIR in Router R2 with new value: 124.602576
Modified S2 policer CIR changes are effective
###################END OF ACTIONS ON SITE-S2##################
##################SITE-S3 POLLED DATA& ACTIONS################
SITE-S3 IP: 3.3.3.3
SITE-S3 TYPE: 2
SITE-S3 MODCOD: 4
Modified CIR Value: 29.66574
Modified PIR Value: 44.49861
Modified S1 policer CIR in Router R1 with new value: 29.66574
Modified S1 policer CIR changes are effective
Modified S2 policer CIR in Router R2 with new value: 29.66574
Modified S2 policer CIR changes are effective
###################END OF ACTIONS ON SITE-S3##################
##################SITE-S4 POLLED DATA& ACTIONS################
SITE-S4 IP: 4.4.4.4
SITE-S4 TYPE: 2
SITE-S4 MODCOD: 12
Modified CIR Value: 24.919874
Modified PIR Value: 37.379811
Modified S1 policer CIR in Router R1 with new value: 24.919874
Modified S1 policer CIR changes are effective
Modified S2 policer CIR in Router R2 with new value: 24.919874
Modified S2 policer CIR changes are effective
###################END OF ACTIONS ON SITE-S4##################
!!!!!!!!!Sleeping for 10 Sec polling interval!!!!!!!!!!!!!!!
##################SITE-S1 POLLED DATA& ACTIONS################
SITE-S1 IP: 1.1.1.1
SITE-S1 TYPE: 1
SITE-S1 MODCOD: 16
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S1##################
##################SITE-S2 POLLED DATA& ACTIONS################
SITE-S2 IP: 2.2.2.2
SITE-S2 TYPE: 1
SITE-S2 MODCOD: 19
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S2##################
##################SITE-S3 POLLED DATA& ACTIONS################
SITE-S3 IP: 3.3.3.3
SITE-S3 TYPE: 2
SITE-S3 MODCOD: 4
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S3##################
##################SITE-S4 POLLED DATA& ACTIONS################
SITE-S4 IP: 4.4.4.4
SITE-S4 TYPE: 2
SITE-S4 MODCOD: 12
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S4##################
!!!!!!!!!Sleeping for 10 Sec polling interval!!!!!!!!!!!!!!!
##################SITE-S1 POLLED DATA& ACTIONS################
SITE-S1 IP: 1.1.1.1
SITE-S1 TYPE: 1
SITE-S1 MODCOD: 16
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S1##################
##################SITE-S2 POLLED DATA& ACTIONS################
SITE-S2 IP: 2.2.2.2
SITE-S2 TYPE: 1
SITE-S2 MODCOD: 19
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S2##################
##################SITE-S3 POLLED DATA& ACTIONS################
SITE-S3 IP: 3.3.3.3
SITE-S3 TYPE: 2
SITE-S3 MODCOD: 4
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S3##################
##################SITE-S4 POLLED DATA& ACTIONS################
SITE-S4 IP: 4.4.4.4
SITE-S4 TYPE: 2
SITE-S4 MODCOD: 12
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S4##################
!!!!!!!!!Sleeping for 10 Sec polling interval!!!!!!!!!!!!!!!
##################SITE-S1 POLLED DATA& ACTIONS################
SITE-S1 IP: 1.1.1.1
SITE-S1 TYPE: 1
SITE-S1 MODCOD: 16
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S1##################
##################SITE-S2 POLLED DATA& ACTIONS################
SITE-S2 IP: 2.2.2.2
SITE-S2 TYPE: 1
SITE-S2 MODCOD: 19
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S2##################
##################SITE-S3 POLLED DATA& ACTIONS################
SITE-S3 IP: 3.3.3.3
SITE-S3 TYPE: 2
SITE-S3 MODCOD: 4
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S3##################
##################SITE-S4 POLLED DATA& ACTIONS################
SITE-S4 IP: 4.4.4.4
SITE-S4 TYPE: 2
SITE-S4 MODCOD: 12
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S4##################
!!!!!!!!!Sleeping for 10 Sec polling interval!!!!!!!!!!!!!!!
##################SITE-S1 POLLED DATA& ACTIONS################
SITE-S1 IP: 1.1.1.1
SITE-S1 TYPE: 1
SITE-S1 MODCOD: 16
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S1##################
##################SITE-S2 POLLED DATA& ACTIONS################
SITE-S2 IP: 2.2.2.2
SITE-S2 TYPE: 1
SITE-S2 MODCOD: 19
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S2##################
##################SITE-S3 POLLED DATA& ACTIONS################
SITE-S3 IP: 3.3.3.3
SITE-S3 TYPE: 2
SITE-S3 MODCOD: 4
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S3##################
##################SITE-S4 POLLED DATA& ACTIONS################
SITE-S4 IP: 4.4.4.4
SITE-S4 TYPE: 2
SITE-S4 MODCOD: 12
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S4##################
!!!!!!!!!Sleeping for 10 Sec polling interval!!!!!!!!!!!!!!!
##################SITE-S1 POLLED DATA& ACTIONS################
SITE-S1 IP: 1.1.1.1
SITE-S1 TYPE: 1
SITE-S1 MODCOD: 16
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S1##################
##################SITE-S2 POLLED DATA& ACTIONS################
SITE-S2 IP: 2.2.2.2
SITE-S2 TYPE: 1
SITE-S2 MODCOD: 19
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S2##################
##################SITE-S3 POLLED DATA& ACTIONS################
SITE-S3 IP: 3.3.3.3
SITE-S3 TYPE: 2
SITE-S3 MODCOD: 4
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S3##################
##################SITE-S4 POLLED DATA& ACTIONS################
SITE-S4 IP: 4.4.4.4
SITE-S4 TYPE: 2
SITE-S4 MODCOD: 12
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S4##################
!!!!!!!!!Sleeping for 10 Sec polling interval!!!!!!!!!!!!!!!
##################SITE-S1 POLLED DATA& ACTIONS################
SITE-S1 IP: 1.1.1.1
SITE-S1 TYPE: 1
SITE-S1 MODCOD: 16
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S1##################
##################SITE-S2 POLLED DATA& ACTIONS################
SITE-S2 IP: 2.2.2.2
SITE-S2 TYPE: 1
SITE-S2 MODCOD: 19
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S2##################
##################SITE-S3 POLLED DATA& ACTIONS################
SITE-S3 IP: 3.3.3.3
SITE-S3 TYPE: 2
SITE-S3 MODCOD: 4
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S3##################
##################SITE-S4 POLLED DATA& ACTIONS################
SITE-S4 IP: 4.4.4.4
SITE-S4 TYPE: 2
SITE-S4 MODCOD: 12
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S4##################
!!!!!!!!!Sleeping for 10 Sec polling interval!!!!!!!!!!!!!!!
##################SITE-S1 POLLED DATA& ACTIONS################
SITE-S1 IP: 1.1.1.1
SITE-S1 TYPE: 1
SITE-S1 MODCOD: 18
Modified CIR Value: 158.23206
Modified PIR Value: 237.34809
Modified S1 policer CIR in Router R1 with new value: 158.23206
Modified S1 policer CIR changes are effective
Modified S2 policer CIR in Router R2 with new value: 158.23206
Modified S2 policer CIR changes are effective
###################END OF ACTIONS ON SITE-S1##################
##################SITE-S2 POLLED DATA& ACTIONS################
SITE-S2 IP: 2.2.2.2
SITE-S2 TYPE: 1
SITE-S2 MODCOD: 19
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S2##################
##################SITE-S3 POLLED DATA& ACTIONS################
SITE-S3 IP: 3.3.3.3
SITE-S3 TYPE: 2
SITE-S3 MODCOD: 4
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S3##################
##################SITE-S4 POLLED DATA& ACTIONS################
SITE-S4 IP: 4.4.4.4
SITE-S4 TYPE: 2
SITE-S4 MODCOD: 12
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S4##################
!!!!!!!!!Sleeping for 10 Sec polling interval!!!!!!!!!!!!!!!
##################SITE-S1 POLLED DATA& ACTIONS################
SITE-S1 IP: 1.1.1.1
SITE-S1 TYPE: 1
SITE-S1 MODCOD: 18
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S1##################
##################SITE-S2 POLLED DATA& ACTIONS################
SITE-S2 IP: 2.2.2.2
SITE-S2 TYPE: 1
SITE-S2 MODCOD: 19
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S2##################
##################SITE-S3 POLLED DATA& ACTIONS################
SITE-S3 IP: 3.3.3.3
SITE-S3 TYPE: 2
SITE-S3 MODCOD: 4
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S3##################
##################SITE-S4 POLLED DATA& ACTIONS################
SITE-S4 IP: 4.4.4.4
SITE-S4 TYPE: 2
SITE-S4 MODCOD: 12
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S4##################
!!!!!!!!!Sleeping for 10 Sec polling interval!!!!!!!!!!!!!!!
##################SITE-S1 POLLED DATA& ACTIONS################
SITE-S1 IP: 1.1.1.1
SITE-S1 TYPE: 1
SITE-S1 MODCOD: 18
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S1##################
##################SITE-S2 POLLED DATA& ACTIONS################
SITE-S2 IP: 2.2.2.2
SITE-S2 TYPE: 1
SITE-S2 MODCOD: 19
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S2##################
##################SITE-S3 POLLED DATA& ACTIONS################
SITE-S3 IP: 3.3.3.3
SITE-S3 TYPE: 2
SITE-S3 MODCOD: 19
Modified CIR Value: 89.00184
Modified PIR Value: 133.50276
Modified S1 policer CIR in Router R1 with new value: 89.00184
Modified S1 policer CIR changes are effective
Modified S2 policer CIR in Router R2 with new value: 89.00184
Modified S2 policer CIR changes are effective
###################END OF ACTIONS ON SITE-S3##################
##################SITE-S4 POLLED DATA& ACTIONS################
SITE-S4 IP: 4.4.4.4
SITE-S4 TYPE: 2
SITE-S4 MODCOD: 12
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S4##################
!!!!!!!!!Sleeping for 10 Sec polling interval!!!!!!!!!!!!!!!
##################SITE-S1 POLLED DATA& ACTIONS################
SITE-S1 IP: 1.1.1.1
SITE-S1 TYPE: 1
SITE-S1 MODCOD: 18
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S1##################
##################SITE-S2 POLLED DATA& ACTIONS################
SITE-S2 IP: 2.2.2.2
SITE-S2 TYPE: 1
SITE-S2 MODCOD: 19
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S2##################
##################SITE-S3 POLLED DATA& ACTIONS################
SITE-S3 IP: 3.3.3.3
SITE-S3 TYPE: 2
SITE-S3 MODCOD: 19
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S3##################
##################SITE-S4 POLLED DATA& ACTIONS################
SITE-S4 IP: 4.4.4.4
SITE-S4 TYPE: 2
SITE-S4 MODCOD: 12
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S4##################
!!!!!!!!!Sleeping for 10 Sec polling interval!!!!!!!!!!!!!!!
##################SITE-S1 POLLED DATA& ACTIONS################
SITE-S1 IP: 1.1.1.1
SITE-S1 TYPE: 1
SITE-S1 MODCOD: 18
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S1##################
##################SITE-S2 POLLED DATA& ACTIONS################
SITE-S2 IP: 2.2.2.2
SITE-S2 TYPE: 1
SITE-S2 MODCOD: 19
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S2##################
##################SITE-S3 POLLED DATA& ACTIONS################
SITE-S3 IP: 3.3.3.3
SITE-S3 TYPE: 2
SITE-S3 MODCOD: 19
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S3##################
##################SITE-S4 POLLED DATA& ACTIONS################
SITE-S4 IP: 4.4.4.4
SITE-S4 TYPE: 2
SITE-S4 MODCOD: 12
CIR/PIR modifications not required for STATE-UNCHANGED  Site
###################END OF ACTIONS ON SITE-S4##################
!!!!!!!!!Sleeping for 10 Sec polling interval!!!!!!!!!!!!!!!
