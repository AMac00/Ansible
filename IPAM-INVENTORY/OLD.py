#!/usr/bin/env python
import json
import urllib.request
import requests
import re
import ssl

hosts = {}
groups = {}
collection = {}
osList = []
osListExceptions = ['no_mgmt', 'update']
updateHosts = []


def getHostsByApp(appName, pLoad):
    appHosts = []
    for item in pLoad:
        host = item['hostname']
        if host is not None:
            app = getAppFromHost(host)
            if (app == appName):
                if (host not in appHosts):
                    appHosts.append(host)
    return appHosts


def buildHostTag(appName, appHost):
    tagBase = "tenant"
    # print("in buildHostTag, hostname={0}".format(appHost))
    if (appHost.startswith('dc')):
        mySide = "a"
    else:
        mySide = "b"

    serverNumber = getServerNumberFromHost(appHost)
    cluster = getClusterFromHost(appHost)
    myTag = tagBase + "_" + mySide + "_" + appName + "_cls_" + cluster + "_" + serverNumber
    # print("in buildHostTag, hostname={0}, host_tag={1}\n".format(appHost,myTag))
    return myTag


def buildHosts():
    global collection, hosts, osListExceptions, updateHosts
    temp_hosts = {}
    for app in collection:
        for host in collection[app]['servers']:
            temp_keys = {}
            if collection[app]['servers'][host]['custom_os_tag'] in osListExceptions:
                if collection[app]['servers'][host]['custom_os_tag'] == 'update':
                    updateHosts.append(host)
                # print("in buildHosts, skipping host {0} due to custom_os_tag = {1}".format(host,collection[app]['servers'][host]['custom_os_tag']))
            else:
                for key in collection[app]['servers'][host]:
                    # print("host = {0}, key = {1}, value = {2}".format(host, key, collection[app]['servers'][host][key]))
                    temp_keys[key] = collection[app]['servers'][host][key]
                temp_hosts[host] = temp_keys

    temp1 = {}
    temp2 = {}
    temp2['hostvars'] = temp_hosts
    temp1['_meta'] = temp2
    hosts = temp1


def getServerNumberFromHost(host):
    return host[3:5]


def getDcFromHost(host):
    return host[7]


def getClusterFromHost(host):
    return host[13:15]


def getAppFromHost(host):
    return host[10:13]


def buildGroups():
    global collection, groups
    group_prefix = 'tenant_'
    temp_ucce_list = []
    temp_ucce_list_a = []
    temp_ucce_list_b = []

    host_list = {}
    cm_pubs = []
    cm_subs = []
    for os in osList:
        temp_os_list = []
        temp_os_list_a = []
        temp_os_list_b = []
        for app in collection:
            # print("app = {0}".format(app))

            temp_app_list = []
            temp_app_list_a = []
            temp_app_list_b = []

            for host in collection[app]['servers']:
                if collection[app]['servers'][host]['custom_os_tag'] not in osListExceptions:
                    host_list[host] = collection[app]['servers'][host]['host_tag']
                else:
                    continue
                # get the dc side
                dc = getDcFromHost(collection[app]['servers'][host]['host_tag'])

                # groups by side
                if (dc == 'a'):
                    # os side a
                    if (os == collection[app]['servers'][host]['custom_os_tag']):
                        temp_os_list_a.append(host)
                    if (app == 'ccm'):
                        serverNumber = getServerNumberFromHost(host)
                        cluster = getClusterFromHost(appHost)
                        if (serverNumber == '01'):
                            # its a pub
                            if host not in cm_pubs:
                                cm_pubs.append(host)
                        else:
                            # its a sub
                            if host not in cm_subs:
                                cm_subs.append(host)
                    elif (app in {'hds', 'rgr', 'rtr', 'lgr', 'ece', 'cpg'}):
                        # print("found side a ucce, host = {0}".format(host))
                        temp_ucce_list_a.append(host)
                        temp_app_list_a.append(host)
                    else:
                        # add all non-ccm and ucce to generic app side list
                        temp_app_list_a.append(host)
                else:
                    # os side b
                    if (os == collection[app]['servers'][host]['custom_os_tag']):
                        temp_os_list_b.append(host)
                    if (app == 'ccm'):
                        serverNumber = getServerNumberFromHost(host)
                        if (serverNumber == '01'):
                            # its a pub
                            if host not in cm_pubs:
                                cm_pubs.append(host)
                        else:
                            # its a sub
                            if host not in cm_subs:
                                cm_subs.append(host)
                    elif (app in {'hds', 'rgr', 'rtr', 'lgr', 'ece', 'cpg'}):
                        # print("found side b ucce, host = {0}".format(host))
                        temp_ucce_list_b.append(host)
                        temp_app_list_b.append(host)
                    else:
                        # add all non-ccm and ucce to generic app side list
                        temp_app_list_b.append(host)

            if app != 'ccm':

                mytemp = {}
                mytemp['hosts'] = temp_app_list_a
                if len(temp_app_list_a) >= 1:
                    groups[group_prefix + app + '_a'] = mytemp
                    temp_app_list.append(group_prefix + app + '_a')
                mytemp = {}
                mytemp['hosts'] = temp_app_list_b
                if len(temp_app_list_b) >= 1:
                    groups[group_prefix + app + '_b'] = mytemp
                    temp_app_list.append(group_prefix + app + '_b')
                mytemp = {}
                mytemp['children'] = temp_app_list
                if len(temp_app_list) >= 1: groups[group_prefix + app] = mytemp

        for myHost in host_list:
            mytemp = {}
            mytemp['hosts'] = myHost
            groups[host_list[myHost]] = mytemp

        mytemp = {}
        mytemp['hosts'] = temp_os_list_a
        if len(temp_os_list_a) >= 1:
            groups[group_prefix + os + '_a'] = mytemp
            temp_os_list.append(group_prefix + os + '_a')
        mytemp = {}
        mytemp['hosts'] = temp_os_list_b
        if len(temp_os_list_b) >= 1:
            groups[group_prefix + os + '_b'] = mytemp
            temp_os_list.append(group_prefix + os + '_b')
        mytemp = {}
        mytemp['children'] = temp_os_list
        if len(temp_os_list) >= 1: groups[group_prefix + os] = mytemp
    for cmpub in cm_pubs:
        cluster = getClusterFromHost(cmpub)
        temp_cluster = []
        temp_cluster_a = []
        temp_cluster_b = []
        dc = getDcFromHost(collection['ccm']['servers'][cmpub]['host_tag'])
        # print("cmpub pub = {0}".format(cmpub))
        mytemp = {}
        mytemp['hosts'] = cmpub
        groups[group_prefix + 'ccm_cls_' + cluster + '_pub'] = mytemp
        temp_cluster.append(cmpub)
        if (dc == 'a'):
            temp_cluster_a.append(cmpub)
        else:
            temp_cluster_b.append(cmpub)
        for cmsub in cm_subs:
            subcluster = getClusterFromHost(cmsub)
            sub_dc = getDcFromHost(collection['ccm']['servers'][cmpub]['host_tag'])
            if cluster == subcluster:
                temp_cluster.append(cmsub)
            if (cluster == subcluster):
                if (sub_dc == 'a'):
                    temp_cluster_a.append(cmsub)
                else:
                    temp_cluster_b.append(cmsub)
        mytemp = {}
        mytemp['children'] = temp_cluster
        if len(temp_cluster) >= 1: groups[group_prefix + 'ccm_cls_' + cluster] = mytemp
        mytemp = {}
        mytemp['hosts'] = temp_cluster_a
        if len(temp_cluster_a) >= 1: groups[group_prefix + 'ccm_cls_' + cluster + '_a'] = mytemp
        mytemp = {}
        mytemp['hosts'] = temp_cluster_b
        if len(temp_cluster_b) >= 1: groups[group_prefix + 'ccm_cls_' + cluster + '_b'] = mytemp

    mytemp = {}
    mytemp['hosts'] = temp_ucce_list_a
    if len(temp_ucce_list_a) >= 1:
        groups[group_prefix + 'ucce_a'] = mytemp
        temp_ucce_list.append(group_prefix + 'ucce_a')
    mytemp = {}
    mytemp['hosts'] = temp_ucce_list_b
    if len(temp_ucce_list_b) >= 1:
        groups[group_prefix + 'ucce_b'] = mytemp
        temp_ucce_list.append(group_prefix + 'ucce_b')
    mytemp = {}
    mytemp['children'] = temp_ucce_list
    if len(temp_ucce_list) >= 1: groups[group_prefix + 'ucce'] = mytemp


def getAttr(appName, appHost, pLoad):
    attrDict = {}
    global osList, osListExceptions
    for item in pLoad:
        mykeys = item.keys()
        host = item['hostname']
        if host is not None:
            app = getAppFromHost(host)
            if (app == appName and host == appHost):
                for key in mykeys:
                    attrDict[key] = item[key]
                    if (key == 'custom_os_tag'):
                        if item[key] not in osList:
                            # print("os not in osList, adding: {0}".format(item[key]))
                            if item[key] not in osListExceptions:
                                osList.append(item[key])

    # build and add host tag
    attrDict['host_tag'] = buildHostTag(appName, appHost)
    return attrDict


def remove_uni(s):
    """remove the leading unicode designator from a string"""
    s2 = s.replace('u\'', '\'')
    s2 = s2.replace('True', 'true')
    s2 = s2.replace('\'', '"')
    s2 = s2.replace('None', '"None"')
    return s2


ipam_server = "ipam.webexcce.io"
ipam_app = "INV"
tenant_code = "wx040"
ipam_app_api_key = "FlluR9QygfJx2HQW8F5KNyeueUzfE3YJ"

url = "https://" + ipam_server + "/api/" + ipam_app + "/addresses/?filter_by=custom_tenant_code&filter_value=" + tenant_code

# python2 syntax
# req = urllib2.Request(url)
# req.add_header("phpipam-token",ipam_app_api_key)
# response = urllib2.urlopen(req)
# python 2

# python3 syntax
headers = {}
headers['phpipam-token'] = ipam_app_api_key
req = urllib.request.Request(url, headers=headers)
response = urllib.request.urlopen(req)
## python3

myresponse = response.read()

# print(myresponse)

myresponse = myresponse.decode('utf8').encode('ascii', errors='ignore')
y = json.loads(myresponse)

appList = []
malformHost = []
data = {}
payload = y['data']
for item in payload:
    mykeys = item.keys()
    myhost = item['hostname']
    # print("myhost = {0}".format(myhost))
    if (myhost is not None):
        if (len(myhost) >= 12):
            # making sure the hostname is long enough to grab the app from
            app = getAppFromHost(myhost)
            if app.isalpha():
                # print(app)
                if app not in appList:
                    appList.append(app)
            else:
                ##print('cannot find app code !!!')
                ##print(item['hostname'])
                if item['hostname'] not in malformHost:
                    malformHost.append(item['hostname'])
print("appList = {0}".format(appList))

for entry in appList:
    ##print(entry)
    hostList = getHostsByApp(entry, payload)
    hostCollection = {}
    for appHost in hostList:
        if appHost is not None:
            hostCollection[appHost] = getAttr(entry, appHost, payload)
    serverCollections = {}
    serverCollections['servers'] = hostCollection
    collection[entry] = serverCollections

# json_object = json.dumps(collection, indent = 4)
# print(json_object)
buildHosts()
hosts_object = json.dumps(hosts, indent=4)
print(hosts_object)
buildGroups()
groups_object = json.dumps(groups, indent=4)
print(groups_object)
# print(updateHosts)