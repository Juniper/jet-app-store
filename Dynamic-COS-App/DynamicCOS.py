#!/usr/bin/env python

"Copyright 2018 Juniper Networks Inc."
"This Dynamic COS App monitors satellite site's modems in 10 seconds interval and detects the changes in modem codes, error noise ratios"\
"and symbol rates. Then computes new COS values based on changes in modem values and generate cos configurations and dynamically pushes"\
"to site's ingess interface of MX based Edge router and also updates dynamic server db with new values"

import os
import re
import sys
import time
import yaml
from glob import glob

import grpc
from pysnmp.entity.rfc3413.oneliner import ntforg
from pysnmp.proto import rfc1902

#for off box compatibility append the location into python path
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'grpc_api'))
import authentication_service_pb2
import firewall_service_pb2
import jnx_addr_pb2
import mgd_service_pb2

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
op_oid1 = mgd_service_pb2.ExecuteOpCommandRequest(request_id=1,
                                                  xml_command=xml_query1,
                                                  out_format= mgd_service_pb2.OPERATION_FORMAT_XML);
xml_query2 = "<get-snmp-object><snmp-object-name>jnxUtilCounter32Value.83.105.116.101.84.121.112.101" \
             "</snmp-object-name></get-snmp-object>"
op_oid2 = mgd_service_pb2.ExecuteOpCommandRequest(request_id=2,
                                                  xml_command=xml_query2,
                                                  out_format= mgd_service_pb2.OPERATION_FORMAT_XML);
xml_query3 = "<get-snmp-object><snmp-object-name>jnxUtilCounter32Value.77.111.100.67.111.100" \
             "</snmp-object-name></get-snmp-object>"
op_oid3 = mgd_service_pb2.ExecuteOpCommandRequest(request_id=3,
                                                  xml_command=xml_query3,
                                                  out_format= mgd_service_pb2.OPERATION_FORMAT_XML);


def _get_network_addr(addr_string):
    """
    Constructs a prpd_common_pb2.NetworkAddress object from the string
    :param addr_string: IPv4 string
    :return: return prpd_common_pb2.NetworkAddress 
    """
    ip = jnx_addr_pb2.IpAddress(addr_string=addr_string)
    return ip


def _authenticateChannel(channel, user, passw, client_id):
    """
    This method authenticates the provided grpc channel.
    """
    sec_stub = authentication_service_pb2.LoginStub(channel)
    cred = authentication_service_pb2.LoginRequest(user_name=user,
                                                   password=passw,
                                                   client_id=client_id)
    res = sec_stub.LoginCheck(cred)
    return res


def Get_Site_Latest_Data():
    """
    This function gets site details like
    existing and latest MODCODS, SITE TYPE, SITE IP
    """
    while(True):
        "Get all Sites MODCOD"
        for i in range(1, n+1):
            "Get site IP"
            command_result = globals()['mgmt_S%s' % i].ExecuteOpCommand(op_oid1)
            result1 = None
            for res in command_result:
                if res.request_id == 1:
                    result1 = res
                    break
            if result1.status == mgd_service_pb2.SUCCESS:
                if re.search (r"<object-value>(\d+.\d+.\d+.\d+)", str(result1.data)):
                    counter1 = re.search (r"<object-value>(\d+.\d+.\d+.\d+)", str(result1.data))
                    SITE_IP = counter1.group(1)
                    print "##################SITE-S{} POLLED DATA& ACTIONS################".format(i)
                    print "SITE-S{} IP: ".format(i) + SITE_IP
                    "Get Site Type i.e enable/disabled"
                    command_result = globals()['mgmt_S%s' %i].ExecuteOpCommand(op_oid2)
                    result2 = None
                    for res in command_result:
                        if res.request_id == 2:
                            result2 = res
                            break
                    if result2.status == mgd_service_pb2.SUCCESS:
                        if re.search (r"<object-value>(\d+)", str(result2.data)):
                            counter2 = re.search (r"<object-value>(\d+)", str(result2.data))
                            SITE_TYPE = counter2.group(1)
                            print "SITE-S{} TYPE: ".format(i) + SITE_TYPE
                            "Get Site MODCOD"
                            command_result = globals()['mgmt_S%s' %i].ExecuteOpCommand(op_oid3)
                            result3 = None
                            for res in command_result:
                                if res.request_id == 3:
                                    result3 = res
                                    break
                            if result3.status == mgd_service_pb2.SUCCESS:
                                if re.search (r"<object-value>(\d+)", str(result3.data)):
                                    counter3 = re.search (r"<object-value>(\d+)", str(result3.data))
                                    SITE_MODCOD = counter3.group(1)
                                    print "SITE-S{} MODCOD: ".format(i) + SITE_MODCOD
                                    if (int(SITE_MODCOD) <= 28):
                                        SITE_SR = globals()['SR_S%s' % i]
                                        SITE_C_CIR = globals()['CIR_S%s' % i]
                                        SITE_C_PIR = SITE_C_CIR*3
                                        SITE_C_MODCOD = globals()['MODCOD_S%s' % i]
                                        SITE_ID = i
                                        Verify_Current_Site_Data(SITE_TYPE, SITE_MODCOD, SITE_SR, SITE_C_MODCOD, SITE_ID)
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


def Verify_Current_Site_Data(SITE_TYPE, SITE_MODCOD, SITE_SR, SITE_C_MODCOD, SITE_ID):
    """
    This function creates new CIR and PIR based on existing and latest site data
    """
    if (SITE_TYPE == 0):
        print "CIR/PIR modifications not required for DISABLED Site"
    else:
        if (SITE_MODCOD == SITE_C_MODCOD):
            print "CIR/PIR modifications not required for STATE-UNCHANGED  Site"
        else:
            mcode = MODCODS[int(SITE_MODCOD)]
            New_CIR = float(mcode)*float(SITE_SR)
            print "Modified CIR Value: {}".format(New_CIR)
            New_PIR = 1.5*New_CIR
            print "Modified PIR Value: {}".format(New_PIR)
            Apply_Cos(New_CIR, New_PIR, SITE_ID)


def Apply_Cos(New_CIR, New_PIR, SITE_ID):
    """
    This function applies COS to MX router in case there is a change in MODCODS
    """
    for i in range(1, n-1):
        print "Modify policer with new CIR values using JET APIS"
        policer_name = 'Policer_S%s' % SITE_ID
        policer_type = firewall_service_pb2.ACL_TWO_COLOR_POLICER
        policer_flag = firewall_service_pb2.ACL_POLICER_FLAG_TERM_SPECIFIC
        color_param = firewall_service_pb2.AclPolicerTwoColor(bw_unit=firewall_service_pb2.ACL_POLICER_RATE_MBPS,
                                                              bandwidth=int(New_CIR),
                                                              burst_unit=firewall_service_pb2.ACL_POLICER_BURST_SIZE_KBYTE,
                                                              burst_size=300,
                                                              discard=firewall_service_pb2.ACL_TRUE)
        policer_params = firewall_service_pb2.AclPolicerParameter(two_color_parameter=color_param)
        policer = firewall_service_pb2.AccessListPolicer(policer_name=policer_name,
                                                         policer_type=policer_type,
                                                         policer_flag=policer_flag,
                                                         policer_params=policer_params)
        print "Pushing policer changes using JET AccessListPolicerChange API"
        result = globals()['fw_R%s' % i].AccessListPolicerReplace(policer)
        if result.status == firewall_service_pb2.ACL_STATUS_EOK:
            print 'Modified policer CIR in Router R{} with new value: {}'.format(i, New_CIR)
            "Verify Modified policer CIR values"

            accessList = firewall_service_pb2.AccessList(acl_name='Filter_S%s' % SITE_ID,
                                    acl_type=firewall_service_pb2.ACL_TYPE_CLASSIC,
                                    acl_family=firewall_service_pb2.ACL_FAMILY_INET)
            policerStats = firewall_service_pb2.AccessListCounter(acl=accessList,
                                                                 counter_name='Policer_S%s-t2' % SITE_ID)

            ret = globals()['fw_R%s' %i].AccessListPolicerCounterGet(policerStats)
            if ret.status == firewall_service_pb2.ACL_STATUS_EOK:
                print 'Modified policer CIR changes are effective'
            else:
                print 'Modified policer CIR changes are not effective'
        else:
            print 'Modification of policer CIR value failed for site S%s' % SITE_ID
        

def Initial_Cos_Configs():
    """
    Initial configuration before start monitoring sites
    """
    for j in range(1, n-1):
        for i in range(1, n+1):
            "Policer API configuration template"
            policer_name = 'Policer_S%s'%i
            policer_type = firewall_service_pb2.ACL_TWO_COLOR_POLICER
            policer_flag = firewall_service_pb2.ACL_POLICER_FLAG_TERM_SPECIFIC
            color_param = firewall_service_pb2.AclPolicerTwoColor(bw_unit=firewall_service_pb2.ACL_POLICER_RATE_MBPS,
                                                                  bandwidth=int(globals()['CIR_S%s'%i]),
                                                                  burst_unit=firewall_service_pb2.ACL_POLICER_BURST_SIZE_KBYTE,
                                                                  burst_size=300,
                                                                  discard=firewall_service_pb2.ACL_TRUE)
            policer_params = firewall_service_pb2.AclPolicerParameter(two_color_parameter=color_param)
            policer =  firewall_service_pb2.AccessListPolicer(policer_name=policer_name,
                                                              policer_type=policer_type,
                                                              policer_flag=policer_flag,
                                                              policer_params=policer_params)

            "Pushing policer configs using JET AccessListPolicerAdd API"
            result = globals()['fw_R%s' %j].AccessListPolicerAdd(policer)
            if result.status != firewall_service_pb2.ACL_STATUS_EOK:
                print "Something went wrong for R%s"%j
                print "Status received %s"%result.status
                exit()
            
            "Firewall Terms configuration template"
            match_src_addr = firewall_service_pb2.AclMatchIpAddress(addr=_get_network_addr("172.16.1.2"),
                                                                    prefix_len=32,
                                                                    match_op=firewall_service_pb2.ACL_MATCH_OP_EQUAL)
            entry_match = firewall_service_pb2.AclEntryMatchInet(match_src_addrs =[match_src_addr])
            entry_adjacency = firewall_service_pb2.AclAdjacency(type=firewall_service_pb2.ACL_ADJACENCY_BEFORE)

            action_counter = firewall_service_pb2.AclActionCounter(counter_name="count2")
            action_policer = firewall_service_pb2.AclActionPolicer(policer=policer)
            non_terminating_action = firewall_service_pb2.AclEntryInetNonTerminatingAction(action_count=action_counter,
                                                                                            action_policer=action_policer)
            terminating_action = firewall_service_pb2.AclEntryInetTerminatingAction(action_accept=firewall_service_pb2.ACL_TRUE)
            entry_action = firewall_service_pb2.AclEntryInetAction(actions_nt=non_terminating_action,               
                                                                   action_t=terminating_action)
            
            single_entry = firewall_service_pb2.AclInetEntry(ace_name="t2",
                                                             ace_op=firewall_service_pb2.ACL_ENTRY_OPERATION_ADD,
                                                             matches=entry_match,
                                                             adjacency=entry_adjacency,
                                                             actions=entry_action)
            acl_entry = firewall_service_pb2.AclEntry(inet_entry=single_entry)
            ace_list =[acl_entry] 

            "Creating filter and mapping terms"
            accessList = firewall_service_pb2.AccessList(acl_name='Filter_S%s' % i,
                                                        acl_type=firewall_service_pb2.ACL_TYPE_CLASSIC,
                                                        acl_family=firewall_service_pb2.ACL_FAMILY_INET,
                                                        acl_flag=firewall_service_pb2.ACL_FLAGS_NONE,
                                                        ace_list=ace_list)
            print "Pushing firewall filter configuration using JET FW AccessListAdd API"
            result = globals()['fw_R%s' %j].AccessListAdd(accessList)
            if result.status != firewall_service_pb2.ACL_STATUS_EOK:
                print "Something went wrong for R%s"%j
                print "Status received %s"%result.status
                exit()
            print "Bind filter configuration template"
            bindobj = firewall_service_pb2.AccessListObjBind(acl=accessList,
                                                            obj_type=firewall_service_pb2.ACL_BIND_OBJ_TYPE_INTERFACE,
                                                            bind_object=globals()['R%s_IF_S%s' %(j, i)],
                                                            bind_direction=firewall_service_pb2.ACL_BIND_DIRECTION_INPUT,
                                                            bind_family=firewall_service_pb2.ACL_FAMILY_INET)
            print "Bind filter to physical interface using JET AccessListBindAdd"
            result = globals()['fw_R%s' %j].AccessListBindAdd(bindobj)
            if result.status != firewall_service_pb2.ACL_STATUS_EOK:
                print "Site_S%s Initial COS configuration activation failed" %i
                print "Status received %s"%result.status
                exit()
            else:
                print "Site_S%s Initial COS configuration activation in Router_R%s is successful" %(i,j)

def notification_send(SITE_IP):
    """
    Notifies site failures to network management server
    """
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



def Main():
    """
    This function handles connections to Sites, Routers and JET firewall and management services
    """
    try:
        "connection handles to site is optional in case polling to sites on SNMP/DyCOS server"
        for i in range(1, n+1):
            creds = grpc.ssl_channel_credentials(open('{}.pem'.format(globals()['S%s_IP' %i])).read())
            channel = grpc.secure_channel(globals()['S%s_IP' %i]+':'+PORT, creds)
            res = _authenticateChannel(channel, USER, PASSWORD, CLIENT_ID)
            print "Authentication "+('success' if res else 'failure')+' for '+globals()['S%s_IP' %i]
            if res is False:
                return
            S_mgmt_stub = mgd_service_pb2.ManagementRpcApiStub(channel)
         
            globals()['mgmt_S%s' % i] = S_mgmt_stub

        "MX router connection and JET service handles"
        for i in range(1, n-1):
            creds = grpc.ssl_channel_credentials(open('{}.pem'.format(globals()['R%s_IP' %i])).read())
            channel = grpc.secure_channel(globals()['R%s_IP' %i]+':'+PORT, creds)
            res = _authenticateChannel(channel, USER, PASSWORD, CLIENT_ID)
            print "Authentication "+('success' if res else 'failure')+' for '+globals()['R%s_IP' %i]
            if res is False:
                return
            
            R_fw_stub = firewall_service_pb2.AclServiceStub(channel)
            R_mgmt_stub = mgd_service_pb2.ManagementRpcApiStub(channel)
            globals()['mgmt_R%s' % i] = R_mgmt_stub
            globals()['fw_R%s' % i] = R_fw_stub

        Initial_Cos_Configs()
        Get_Site_Latest_Data()

    except KeyboardInterrupt:
         pass
    except Exception as tx:
        print '%s' % (tx.message)
    return
if __name__ == '__main__':
    Main()
