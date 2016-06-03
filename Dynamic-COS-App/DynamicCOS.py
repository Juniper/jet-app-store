#!/usr/bin/env python
"This Dynamic COS App monitors satellite site's modems in 10 seconds interval and detects the changes in modem codes, error noise ratios"\
"and symbol rates. Then computes new COS values based on changes in modem values and generate cos configurations and dynamically pushes"\
"to site's ingess interface of MX based Edge router and also updates dynamic server db with new values"

import time, re, yaml
from glob import glob

# JET login imports
from jnpr.jet.JetHandler import *

#firewall
from jnpr.jet.firewall import *
from jnpr.jet.firewall.ttypes import *

#Management
from jnpr.jet.management import *
from jnpr.jet.management.ttypes import *
from pysnmp.entity.rfc3413.oneliner import ntforg
from pysnmp.proto import rfc1902

with open(glob('input.yml')[0]) as fh:
    data = yaml.load(fh.read())
    for k,v in data.iteritems():
        globals()[k] = v

#"O3B predefined MODCODS"
MODCODS = {1:0.490243, 2:0.656448,3:0.789412, 4:0.988858, 5:1.188304, 6:1.322253, 7:1.487473, 8:1.587196, 9:1.654663,
           10:1.766451, 11:1.788612, 12:1.779991, 13:1.980636, 14:2.228124, 15:2.478562, 16:2.646012, 17:2.679207,
           18:2.637201, 19:2.966728, 20:3.165623, 21:3.300184, 22:3.523143, 23:3.567342, 24:3.703295, 25:3.951571,
           26:4.119540, 27:4.397854, 28:4.453027}

#"Symbol rate db"
v1n1 = float(2); v1n2 = float(2); v1r = 180; v1m = float(2)
v2n1 = float(3); v2n2 = float(1); v2r = 140; v2m= float(3)
SR_S1 = int(v1r/(v1n1+v1n2/v1m))
SR_S2 = int(v2r/(v2n1+v2n2/v2m))
SR_S3 = int(SR_S1/v1m)
SR_S4 = int(SR_S2/v2m)

MODCOD_ = {}
CIR_ = {}
PIR_ = {}
TYPE_ = {}
SR_ = {}
_IF_ = {}
mgmt_ = {}

#"SNMP OIDS to GET MODCODS, SITE TYPE, etc"
xml_query1 = "<get-snmp-object><snmp-object-name>jnxUtilStringValue.83.105.116.101.67.116.114.73.112.65.100.100.114" \
             "</snmp-object-name></get-snmp-object>"
op_oid1 = OperationCommand(xml_query1, in_format=OperationFormatType.OPERATION_FORMAT_XML,
                           out_format=OperationFormatType.OPERATION_FORMAT_XML);
xml_query2 = "<get-snmp-object><snmp-object-name>jnxUtilCounter32Value.83.105.116.101.84.121.112.101" \
             "</snmp-object-name></get-snmp-object>"
op_oid2 = OperationCommand(xml_query2, in_format=OperationFormatType.OPERATION_FORMAT_XML,
                           out_format=OperationFormatType.OPERATION_FORMAT_XML);
xml_query3 = "<get-snmp-object><snmp-object-name>jnxUtilCounter32Value.77.111.100.67.111.100" \
             "</snmp-object-name></get-snmp-object>"
op_oid3 = OperationCommand(xml_query3, in_format=OperationFormatType.OPERATION_FORMAT_XML,
                           out_format=OperationFormatType.OPERATION_FORMAT_XML);

#"This function gets site details like existing and latest MODCODS, SITE TYPE, SITE IP"
def Get_Site_Latest_Data():
    while(True):
        "Get all Sites MODCOD"
        for i in range(1, n+1):
            "Get site IP"
            result1 = globals()['mgmt_S%s' %i].ExecuteOpCommand(op_oid1)
            if result1.status.err_code == 0:
                if re.search (r"<object-value>(\d+.\d+.\d+.\d+)", str(result1)):
                    counter1 = re.search (r"<object-value>(\d+.\d+.\d+.\d+)", str(result1))
                    SITE_IP = counter1.group(1)
                    print "##################SITE-S{} POLLED DATA& ACTIONS################".format(i)
                    print "SITE-S{} IP: ".format(i) + SITE_IP
                    "Get Site Type i.e enable/disabled"
                    result2 = globals()['mgmt_S%s' %i].ExecuteOpCommand(op_oid2)
                    if result2.status.err_code == 0:
                        if re.search (r"<object-value>(\d+)", str(result2)):
                            counter2 = re.search (r"<object-value>(\d+)", str(result2))
                            SITE_TYPE = counter2.group(1)
                            print "SITE-S{} TYPE: ".format(i) + SITE_TYPE
                            "Get Site MODCOD"
                            result3 = globals()['mgmt_S%s' %i].ExecuteOpCommand(op_oid3)
                            if result3.status.err_code == 0:
                                if re.search (r"<object-value>(\d+)", str(result3)):
                                    counter3 = re.search (r"<object-value>(\d+)", str(result3))
                                    SITE_MODCOD = counter3.group(1)
                                    print "SITE-S{} MODCOD: ".format(i) + SITE_MODCOD
                                    if (int(SITE_MODCOD) <= 28):
                                        SITE_SR = globals()['SR_S%s' % i]
                                        SITE_C_CIR = globals()['CIR_S%s' % i]
                                        SITE_C_PIR = SITE_C_CIR*3
                                        SITE_C_MODCOD = globals()['MODCOD_S%s' % i]
                                        Verify_Current_Site_Data(SITE_TYPE, SITE_MODCOD, SITE_SR, SITE_C_MODCOD)
                                        globals()['TYPE_S%s' % i] = SITE_TYPE
                                        globals()['MODCOD_S%s' % i] = SITE_MODCOD
                                        print "###################END OF ACTIONS ON SITE-{}##################\n".format(i)
                                    else:
                                        print "Invalid MODCOD"
                                else:
                                    print "Unable to GET SITE-{} MODCOD".format(i)
                            else:
                                print "Unable to GET SITE-{} MODCOD".format(i)
                        else:
                            print "Unable to GET SITE-{} TYPE".format(i)
                    else:
                        print "Unable to GET SITE-{} TYPE".format(i)
                else:
                    print "Unable to GET SITE-{} IP".format(i)
                    notification_send(SITE_IP)
            else:
                print "Unable to GET SITE-{} IP".format(i)
        print "!!!!!!!!!Sleeping for 10 Sec polling interval!!!!!!!!!!!!!!!"
        time.sleep(poll_interval)
    print "Closing connection"

#"This function creates new CIR and PIR based on existing and latest site data"
def Verify_Current_Site_Data(SITE_TYPE, SITE_MODCOD, SITE_SR, SITE_C_MODCOD):
    if (SITE_TYPE == 0):
        print "CIR/PIR modifications not required for DISABLED Site"
    else:
        if (SITE_MODCOD == SITE_C_MODCOD):
            print "CIR/PIR modifications not required for STATE-UNCHANGED  Site"
        else:
            mcode = MODCODS[int(SITE_MODCOD)]
            New_CIR = float(mcode)*float(SITE_SR)
            print "Modified CIR Value:", New_CIR
            New_PIR = 1.5*New_CIR
            print "Modified PIR Value:", New_PIR
            Apply_Cos(New_CIR,New_PIR)

#"This function applies COS to MX router in case there is a change in MODCODS"
def Apply_Cos(New_CIR,New_PIR):
    for i in range(1, n-1):
        "Modify policer with new CIR values using JET APIS"
        policer = AccessListPolicer()
        policer.policer_params = PolicerTwoColor()
        policer.policer_flag = PolicerFlags.TERM_SPECIFIC
        policer.policer_params.bandwidth = New_CIR
        policer.policer_params.bw_unit = PolicerRate.MB
        policer.policer_params.burst_size = 300
        policer.policer_params.burst_unit = PolicerRate.BYTE
        policer.policer_params.discard = AclBooleanType.TRUE
        policer.policer_name= 'Policer_S%s' % i
        "Pushing policer changes using JET AccessListPolicerChange add API"

        result = globals()['fw_R%s' %i].AccessListPolicerChange(policer)
        if result.err_code == 0:
            print 'Modified policer CIR in Router R%d with new value:' %i, New_CIR
            "Verify Modified policer CIR values"
            filter = AccessList()
            filter.acl_name = 'Filter_S%s' % i
            filter.acl_type = AccessListTypes.CLASSIC
            filter.acl_family = AccessListFamilies.INET
            policerStats = AccessListPolicerCounter()
            policerStats.acl = filter
            policerStats.policer_name = 'Policer_S%s' % i
            ret = globals()['fw_R%s' %i].AccessListPolicerCounterStatsGet(policerStats)
            if result.err_code == 0:
                print 'Modified policer CIR changes are effective'
            else:
                print 'Modified policer CIR changes are not effective'
        else:
            print 'Modification of policer CIR value failed for site S%s' %i
        "Can be done further verifications with cli commands using JET management APIs like below"
        # print 'Invoked AccessListPolicerCounterStatsGet:\nresult= ', ret
        #
        # op_command = OperationCommand("request pfe execute command \"show filter\" target fpc0 | match S%s" %i,
        #                 OperationFormatType.OPERATION_FORMAT_CLI, OperationFormatType.OPERATION_FORMAT_XML);
        #
        # result = globals()['mgmt_%s' %j].ExecuteOpCommand(op_command)

#"Initial configuration before start monitoring sites"
def Initial_Cos_Configs():

    for j in range(1, n-1):
        for i in range(1, n+1):
            "Policer API configuration template"
            policer = AccessListPolicer()
            policer.policer_params = PolicerTwoColor()
            policer.policer_flag = PolicerFlags.TERM_SPECIFIC
            policer.policer_params.bandwidth = int(globals()['CIR_S%s' % i])
            policer.policer_params.bw_unit = PolicerRate.MB
            policer.policer_params.burst_size = 300
            policer.policer_params.burst_unit = PolicerRate.BYTE
            policer.policer_params.discard = AclBooleanType.TRUE
            policer.policer_name= 'Policer_S%s' % i

            "Pushing policer configs using JET AccessListPolicerAdd add API"
            result = globals()['fw_R%s' %j].AccessListPolicerAdd(policer)

            "Firewall Terms configuration template"
            term2 = AclInetEntry()
            term2.ace_name = "t2"
            term2.ace_op = AclEntryOperation.ADD
            term2match1 = AclEntryMatchInet()
            op=AclMatchOperation.EQUAL
            src2 = AclMatchIpAddress("172.16.1.2", 32, op)
            term2match1.match_src_addrs = [src2]
            term2Action1 = AclEntryInetAction()
            term2Action1.action_t = AclEntryInetTerminatingAction()
            term2Action1.action_t.action_accept = AclBooleanType.TRUE
            term2Action1_nt = AclEntryInetNonTerminatingAction()
            term2Action1_nt.action_count = AclActionCounter("count2")
            term2Action1.actions_nt = []
            term2Action1_nt.action_police=AclActionPolicer()
            "Mapping above created policer to term2"
            term2Action1_nt.action_police.policer = policer
            term2Action1.actions_nt.append(term2Action1_nt)
            term2.actions=[]
            term2.actions.append(term2Action1)
            term2.matches=[]
            term2.matches.append(term2match1)
            tlist2 = AclEntry()
            tlist2.inet_entry = term2

            "Creating filter and mapping terms"
            filter = AccessList()
            filter.acl_name = 'Filter_S%s' % i
            filter.acl_type = AccessListTypes.CLASSIC
            filter.acl_family = AccessListFamilies.INET
            filter.acl_flag = AccessListFlags.NONE
            filter.ace_list=[tlist2]

            "Pushing firewall filer configuration using JET FW AccessListAdd Add API"
            result = globals()['fw_R%s' %j].AccessListAdd(filter)

            "Bind filter configuration template"
            bindobj = AccessListObjBind()
            bindobj.acl = filter
            bindobj.obj_type = AccessListObjType.FILTER_OBJ_INTERFACE
            bindobj.bind_object = globals()['R%s_IF_S%s' %(j, i)]
            bindobj.bind_direction = AclBindDirection.INPUT
            bindobj.bind_family = AccessListFamilies.INET

            "Bind filter to physical interface using JET AccessListBindAdd"
            result = globals()['fw_R%s' %j].AccessListBindAdd(bindobj)
            if result.err_code != 0:
                print "Site_S%s Initial COS configuration activation failed" %i

            else:
                print "Site_S%s Initial COS configuration activation in Router_R%s is successful" %(i,j)

#Notifies site failures to network management server
def notification_send(SITE_IP):
    ntfOrg = ntforg.NotificationOriginator()

    #ntforg.CommunityData('public', mpModel=0),
    errorIndication = ntfOrg.sendNotification(
        ntforg.CommunityData(COMMUNITY, mpModel=0),
        ntforg.UdpTransportTarget((NOC_SERVER, SNMP_PORT)),
        'trap',
        '1.3.6.1.4.1.20408.4.1.1.2.0.432',
        ('1.3.6.1.2.1.1.3.0', 12345),
        ('1.3.6.1.6.3.18.1.3.0', SITE_IP),
        ('1.3.6.1.6.3.1.1.4.3.0', '1.3.6.1.4.1.20408.4.1.1.2'),
        ('1.3.6.1.2.1.1.1.0', "Down"),
    )
    print "Sent trap to manager"
    if errorIndication:
        print('Notification not sent: %s' % errorIndication)

#"This function handles connections to Sites, Routers and JET firewall and management services"
def Main():
    try:
        "connection handles to site is optional in case polling to sites on SNMP/DyCOS server"
        for i in range(1, n+1):
            S_handle = JetHandler()
            S_handle.OpenRequestResponseSession(device=globals()['S%s_IP' %i], port=PORT, user=USER, password=PASSWORD,client_id=CLIENT_ID)
            S_mgmt =S_handle.GetManagementService()
            globals()['mgmt_S%s' % i] = S_mgmt

        "MX router connection and JET service handles"
        for i in range(1, n-1):
            R_handle = JetHandler()
            R_handle.OpenRequestResponseSession(device=globals()['R%s_IP' %i], port=PORT, user=USER, password=PASSWORD, client_id=CLIENT_ID)
            R_fw = R_handle.GetFirewallService()
            R_mgmt =R_handle.GetManagementService()
            globals()['mgmt_R%s' % i] = R_mgmt
            globals()['fw_R%s' % i] = R_fw

        Initial_Cos_Configs()
        Get_Site_Latest_Data()

    except KeyboardInterrupt:
         pass
    except Exception as tx:
        print '%s' % (tx.message)
    return
if __name__ == '__main__':
    Main()
