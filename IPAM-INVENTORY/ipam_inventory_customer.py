#!/usr/bin/python3
# Requests provide HTTP method actions
import urllib3
import requests
from requests.exceptions import HTTPError
# Logging for you know logging
import logging
# Used for input arguments
import argparse
import json
from sys import argv
# Use to search for portions of string in list
from builtins import any as search_any


# Customer Number

__customer_number__ = 'wx040'

# System Variables
__pre_prod_info__ = {
    'ipam_server': 'ipam.webexcce.io',
    'ipam_app': 'INV',
    'ipam_app_api_key': 'FlluR9QygfJx2HQW8F5KNyeueUzfE3YJ'
}

__production_info__ = {
    'ipam_server': 'ipam.mgmt.webexcce.com',
    'ipam_app': 'INV',
    'ipam_app_api_key': 'B-rq5bns1RK0jvOK4sRe2ebD0kK5EIQV'
}

__info__ = __pre_prod_info__

__groups__ = {
    'os': {
        'windows': ['rgr', 'hds', 'cpg', 'cvp', 'cvr', 'ops', 'adc'],
        'vos': ['ccm', 'sso', 'fin', 'uic', 'clc', 'imp', 'ans', 'ipm'],
        'linux': ['portal']
    },
    'app_groups': {
        'app_ucce': ['rgr', 'hds', 'cpg'],
        'app_cvp': ['cvp', 'ops', 'cvr']
    },
    'allowed_ip_address': ('10.201', '10.202','10.1')
}


def __fun__main__(__info__):
    # Set Logging Level's
    try:
        # Set logging information
        logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
        logger = logging.getLogger("ipam-inventory")
        logger.debug("Start {0} application with {0} logging".format(logger.name, logger.level))
    except:
        print("Failed to set logging level")
        # Fail the entire task, this should NEVER fail
        quit()
    # Set Arg input for script
    try:
        argparser = argparse.ArgumentParser()
        argparser.add_argument('--list', action='store_true', required=False)
        argparser.add_argument('--host', action='store', type=str, required=False)
        args = argparser.parse_args()
        if args.list:
            logger.debug("Collected arguments for List")
        if args.host:
            logger.debug("Collected arguments for Hosts")
    except:
        logger.warning("Failed Parsing function")
    # Build IPAM requests
    try:
        # Set static instance ipam url --
        '''
         This a really bad solution for pulls on phpIPAM but in the interest of time ( >10min ), it will do. 
        '''
        __ipam_url__ = 'https://{0}/api/{1}'.format(__info__['ipam_server'], __info__['ipam_app'])
        # Set Key for IPAM auth, it doesn't use PWD or Cookies.
        __ipam_key__ = {'phpipam-token': __info__['ipam_app_api_key']}
        # Create the Response list
        __info__['tenant_response'] = {}
        # Create a Single Session context for re-use
        __session__ = requests.session()
        # Pull all addresses
        __ipam_tail__ = '/addresses/'
        logger.debug("__ipam_tail__ = {0}".format(__ipam_tail__))
        __ipam_full_url__ = "{0}{1}".format(__ipam_url__, __ipam_tail__)
        logger.debug("Request URL = {0}".format(__ipam_full_url__))
        logger.debug("Headers = {0}".format(__ipam_key__))
        try:
            # This is only used to remove the warning label on the console - Its annoying
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            # The actual requests to pull server information from PHP-IPAM
            __response__ = __session__.request("GET", __ipam_full_url__, headers=__ipam_key__, verify=False)
            # Validate return codes
            __response__.raise_for_status()
            if __response__.status_code == requests.codes.ok:
                logger.debug("Return status code is  {0}, so it worked".format(__response__.status_code))
                # logger.debug("Return message = {0}".format(__response__.content))
                __data__ = __response__.json()
                __info__['tenant_response'] = __data__
            else:
                logger.warning("Return status code is  {0}, not great.".format(__response__.status_code))
                return ()
        except HTTPError as http_err:
            logger.warning('HTTP error occurred: {0}'.format(http_err))
            return ()
        except Exception as err:
            logger.warning('Other error occurred: {0}'.format(err))
            return ()
    except:
        logger.warning("Failed at IPAM URL function")
        return ()
    # Inventory Build - Parse __info__ dictionary for elements need for inventory
    try:
        # Parse all the responses for each tenant
        __inventory__ = {
            '_meta': {
                'hostvars': {}
            },
            'all_servers': []
        }
        __ccm_hosts_list__ = []
        # Build the _meta data for all servers returned by IPAM
        for servers in __info__['tenant_response']['data']:
            logger.debug("Working on hostname = {0} and IP = {1} ".format(servers['hostname'],servers['ip']))
            # Parse IP address to validate is in acceptable list
            __server_ip_oct__ = servers['ip'].split(".")
            if servers['hostname'] and "{0}.{1}".format(__server_ip_oct__[0], __server_ip_oct__[1]) in __groups__['allowed_ip_address'] and "{0}".format(__customer_number__) in servers['hostname']:
                logger.debug("Working on hostname = {0} and IP = {1} ".format(servers['hostname'], servers['ip']))
                '''
                Add all servers go a all_servers group
                '''
                # Add all attributes to _meta data - This provides host variables per server
                __inventory__['_meta']['hostvars'][servers['hostname']] = servers
                if "all_servers" not in __inventory__.keys():
                    __inventory__["all_servers"] = []
                # Import all hosts without groups
                if servers['hostname'] not in __inventory__["all_servers"]:
                   __inventory__["all_servers"].append(servers['hostname'])
                '''
                Building Groups based on variables and hostname parsing
                1. Parse hostname for 
                    1. Datacenter, 
                    2. Application
                    3. Cluster Number 
                2. Pair Hostname Parsing into groups
                3. Pair OS's based on Application 
                '''
                # Parse Hostname
                try:
                    # Test name for "."'s and pull the true hostname
                    if "." in servers['hostname']:
                        __host_name__ = servers['hostname'].split(".")[0]
                    else:
                        __host_name__ = servers['hostname']
                    logger.debug("Datacenter = {0}".format(__host_name__))
                    # Parse Datacenter
                    __host_dc__ = __host_name__[:3].lower()
                    __host_number__ = __host_name__[3:5].lower()
                    __cust_number__ = __host_name__[5:10].lower()
                    __host_app__ = __host_name__[10:13].lower()
                    __host_cluster_number__ = __host_name__[13:].lower()
                    logger.debug(
                        'DC = {0} and Host # = {1} and Cust # = {2} and App = {3} and Cluster = {4}'.format(__host_dc__,
                                                                                                            __host_number__,
                                                                                                            __cust_number__,
                                                                                                            __host_app__,
                                                                                                            __host_cluster_number__))
                    '''
                        Start Name breakdown correlation based on Tenant_CustNum_App_DN_ClustersNum_ServerNumber

                        example: 
                        [tenant_CCM_DEN_01_01]
                        host

                        [tenant_CCM_DEN_01]
                        tenant_CCM_DEN_01_01
                        tenant_CCM_DEN_01_02
                        tenant_CCM_DEN_01_03

                        [tenant_CCM_DEN]
                        tenant_CCM_DEN_01
                        tenant_CCM_DEN_02

                        [tenant_CCM]
                        tenant_CCM_DEN
                        tenant_CCM_AUS

                    '''
                    # Builds a group per host
                    try:
                        if "tenant_{0}_{1}_cls{2}_srv{3}".format( __host_app__, __host_dc__,
                                                               __host_cluster_number__,
                                                               __host_number__) not in __inventory__.keys():
                            __inventory__[
                                "tenant_{0}_{1}_cls{2}_srv{3}".format(__host_app__, __host_dc__,
                                                                    __host_cluster_number__, __host_number__)] = []
                        if servers['hostname'] not in __inventory__[
                            "tenant_{0}_{1}_cls{2}_srv{3}".format(__host_app__, __host_dc__,
                                                                __host_cluster_number__, __host_number__)]:
                            __inventory__[
                                "tenant_{0}_{1}_cls{2}_srv{3}".format(__host_app__, __host_dc__,
                                                                    __host_cluster_number__, __host_number__)].append(
                                servers['hostname'])
                    except:
                        logger.warning(
                            "Error parsing for Tenant_App_DN_ClustersNum_ServerNumber:Child for {0}".format(
                                servers['hostname']))
                    # Build and Validate Tenant_App_DC_ClustersNum :Child Group
                    try:
                        if "tenant_{0}_{1}_cls{2}".format(__host_app__, __host_dc__,
                                                           __host_cluster_number__) not in __inventory__.keys():
                            __inventory__["tenant_{0}_{1}_cls{2}".format(__host_app__, __host_dc__,
                                                                          __host_cluster_number__)] = {
                                'children': []
                            }
                        if "tenant_{0}_{1}_cls{2}_srv{3}".format(__host_app__, __host_dc__,
                                                               __host_cluster_number__, __host_number__) not in \
                                __inventory__[
                                    "tenant_{0}_{1}_cls{2}".format(__host_app__, __host_dc__,
                                                                    __host_cluster_number__)]['children']:
                            __inventory__["tenant_{0}_{1}_cls{2}".format(__host_app__, __host_dc__,
                                                                          __host_cluster_number__)]['children'].append(
                                "tenant_{0}_{1}_cls{2}_srv{3}".format(__host_app__, __host_dc__,
                                                                    __host_cluster_number__, __host_number__))
                    except:
                        logger.warning("Error attaching {0} in {1}".format(
                            "tenant_{0}_{1}_cls{2}_srv{3}".format(__host_app__, __host_dc__,
                                                                __host_cluster_number__, __host_number__),
                            "tenant_{0}_{1}_cls{2}".format(__host_app__, __host_dc__,
                                                            __host_cluster_number__)))
                    # Build and Validate Tenant_App_DC:Child Group
                    try:
                        if "tenant_{0}_{1}".format(__host_app__,
                                                       __host_dc__) not in __inventory__.keys():
                            __inventory__["tenant_{0}_{1}".format(__host_app__, __host_dc__)] = {
                                'children': []
                            }
                        if "tenant_{0}_{1}_cls{2}".format(__host_app__, __host_dc__,
                                                           __host_cluster_number__) not in \
                                __inventory__["tenant_{0}_{1}".format( __host_app__, __host_dc__)][
                                    'children']:
                            __inventory__["tenant_{0}_{1}".format(__host_app__, __host_dc__)][
                                'children'].append(
                                "tenant_{0}_{1}_cls{2}".format(__host_app__, __host_dc__,
                                                                __host_cluster_number__))
                    except:
                        logger.warning("Error attaching {0} in {1}".format(
                            "tenant_{0}_{1}_{2}".format(__host_app__, __host_dc__,
                                                            __host_cluster_number__),
                            "tenant_{0}_{1}".format(__host_app__, __host_dc__)))
                    # Build and Validate Tenant_App:Child Group
                    try:
                        if "tenant_{0}".format(__host_app__) not in __inventory__.keys():
                            __inventory__["tenant_{0}".format(__host_app__)] = {
                                'children': []
                            }
                        if "tenant_{0}_{1}".format(__host_app__, __host_dc__) not in \
                                __inventory__["tenant_{0}".format(__host_app__)]['children']:
                            __inventory__["tenant_{0}".format(__host_app__)]['children'].append(
                                "tenant_{0}_{1}".format(__host_app__, __host_dc__))
                    except:
                        logger.warning("Error attaching {0} in {1}".format(
                            "tenant_{0}_{1}".format(__host_app__, __host_dc__),
                            "tenant_{0}".format(__host_app__)))
                    '''
                    Start OS pairing

                    example :
                    -------OS Breakdown --------
                    [tenant_WX005_vos_den]
                    tenant_WX005_CCM_DEN

                    [tenant_WX005_vos_aus]
                    tenant_WX005_CCM_AUS

                    [tenant_WX005_vos]
                    tenant_WX005_CCM_DEN
                    tenant_WX005_CCM_AUS
                    '''
                    # Build and Add Group to Tenant_OS_DC :Child Group
                    try:
                        for __os__ in __groups__['os']:
                            if __host_app__ in __groups__['os'][__os__]:
                                # Add OS-Datacenter-Cluster to OS-Datacenter Group
                                if "tenant_{0}_{1}".format(__os__,
                                                               __host_dc__) not in __inventory__.keys():
                                    __inventory__["tenant_{0}_{1}".format(__os__, __host_dc__)] = {
                                        'children': []
                                    }
                                # Add Server Group ( App,DC,Cluster)  to OS Group
                                if "tenant_{0}_{1}_{2}".format(__host_app__, __host_dc__) not in \
                                        __inventory__[
                                            "tenant_{0}_{1}".format(__os__, __host_dc__)][
                                            'children']:
                                    __inventory__["tenant_{0}_{1}".format(__os__, __host_dc__)][
                                        'children'].append(
                                        "tenant_{0}_{1}".format(__host_app__, __host_dc__))
                                # Add OS Datacenter Group to Master OS Group
                                if "tenant_{0}".format( __os__) not in __inventory__.keys():
                                    __inventory__["tenant_{0}".format(__os__)] = {
                                        'children': []
                                    }
                                if "tenant_{0}_{1}".format(__host_app__, __host_dc__) not in \
                                        __inventory__["tenant_{0}".format(__os__)]['children']:
                                    __inventory__["tenant_{0}".format(__os__)]['children'].append(
                                        "tenant_{0}_{1}".format(__host_app__, __host_dc__))
                    except:
                        logger.warning("Error parsing for Tenant_OS for {0}".format(servers['hostname']))
                    '''
                        Applicaiton Pairing

                    example :
                    [tenant_WX005_UCCE_den]
                    tenant_WX005_RGR_DEN
                    tenant_WX005_HDS_DEN

                    [tenant_WX005_UCCE]
                    tenant_WX005_UCCE_den
                    tenant_WX005_UCCE_aus

                    '''
                    # Build and Add Group to Tenant_AppGroup_DC
                    try:
                        for __app_group__ in __groups__['app_groups']:
                            if __host_app__ in __groups__['app_groups'][__app_group__]:
                                # Test and Build Teneant_AppGroup_DC
                                if 'tenant_{0}_{1}_{2}'.format(__cust_number__, __app_group__,
                                                               __host_dc__) not in __inventory__.keys():
                                    __inventory__[
                                        'tenant_{0}_{1}_{2}'.format(__cust_number__, __app_group__, __host_dc__)] = {
                                        'children': []
                                    }
                                # Add Tenant_App_DC_Cluster to Tenant_AppGroup_DC
                                if 'tenant_{0}_{1}_{2}'.format(__cust_number__, __host_app__, __host_dc__) not in \
                                        __inventory__[
                                            'tenant_{0}_{1}_{2}'.format(__cust_number__, __app_group__, __host_dc__)][
                                            'children']:
                                    __inventory__[
                                        'tenant_{0}_{1}_{2}'.format(__cust_number__, __app_group__, __host_dc__)][
                                        'children'].append(
                                        'tenant_{0}_{1}_{2}'.format(__cust_number__, __host_app__, __host_dc__))
                                # Add Tenant_AppGroup_DC to Tenant_AppGroup
                                if "tenant_{0}_{1}".format(__cust_number__, __app_group__) not in __inventory__.keys():
                                    __inventory__["tenant_{0}_{1}".format(__cust_number__, __app_group__)] = {
                                        'children': []
                                    }
                                if 'tenant_{0}_{1}_{2}'.format(__cust_number__, __app_group__, __host_dc__) not in \
                                        __inventory__["tenant_{0}_{1}".format(__cust_number__, __app_group__)][
                                            'children']:
                                    __inventory__['tenant_{0}_{1}'.format(__cust_number__, __app_group__)][
                                        'children'].append(
                                        'tenant_{0}_{1}_{2}'.format(__cust_number__, __app_group__, __host_dc__))
                    except:
                        logger.warning("Error looping for Tenant_AppGroups for {0}".format(servers['hostname']))
                except:
                    logger.warning("Failure on {0} to parse name".format(servers['hostname']))
        print(json.dumps(__inventory__))
    except:
        logger.warning("Error parsing the return information in tenant_response")
    return (__info__)


# Run Main Program
if __name__ == "__main__":
    __return__ = __fun__main__(__info__)

