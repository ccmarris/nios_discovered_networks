#!/usr/bin/env python3
#vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
'''

 Description:

    Extract a list of discovered networks not in IPAM

 Requirements:
   Python 3.8+

 Author: Chris Marrison

 Date Last Updated: 20240531

 Todo:

 Copyright (c) 2024 Chris Marrison / Infoblox

 Redistribution and use in source and binary forms,
 with or without modification, are permitted provided
 that the following conditions are met:

 1. Redistributions of source code must retain the above copyright
 notice, this list of conditions and the following disclaimer.

 2. Redistributions in binary form must reproduce the above copyright
 notice, this list of conditions and the following disclaimer in the
 documentation and/or other materials provided with the distribution.

 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
 FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
 INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
 BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
 LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
 ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 POSSIBILITY OF SUCH DAMAGE.

'''
__version__ = '0.0.9'
__author__ = 'Chris Marrison'
__author_email__ = 'chris@infoblox.com'
__license__ = 'BSD'

import logging
import requests
import argparse
import configparser
import time
import csv
import sys
from rich import print
from rich.console import Console
from rich.table import Table

def parseargs():
    '''
    Parse Arguments Using argparse

    Parameters:
        None

    Returns:
        Returns parsed arguments
    '''
    description = 'NIOS Fixed Address Utility'
    parse = argparse.ArgumentParser(description=description)
    parse.add_argument('-c', '--config', type=str, default='gm.ini',
                        help="Override ini file")
    parse.add_argument('-f', '--file', type=str, default='',
                        help='Output CSV to file')
    parse.add_argument('-F', '--format', type=str, default='table',
                        help='Report display format [csv, table]')
    parse.add_argument('-n', '--not_in_ipam', action='store_true', 
                        help="Report only networks that are not in IPAM")
    parse.add_argument('-p', '--page', type=int, default=5,
                        help='Page size to use for retrieving discovered devices')
    parse.add_argument('-d', '--debug', action='store_true', 
                        help="Enable debug messages")

    return parse.parse_args()


def read_ini(ini_filename):
    '''
    Open and parse ini file

    Parameters:
        ini_filename (str): name of inifile

    Returns:
        config :(dict): Dictionary of BloxOne configuration elements

    '''
    # Local Variables
    cfg = configparser.ConfigParser()
    config = {}
    ini_keys = ['gm', 'api_version', 'valid_cert', 'user', 'pass' ]

    # Attempt to read api_key from ini file
    try:
        cfg.read(ini_filename)
    except configparser.Error as err:
        logging.error(err)

    # Look for NIOS section
    if 'NIOS' in cfg.keys():
        for key in ini_keys:
            # Check for key in BloxOne section
            if key in cfg['NIOS']:
                config[key] = cfg['NIOS'][key].strip("'\"")
                logging.debug('Key {} found in {}: {}'.format(key, ini_filename, config[key]))
            else:
                logging.warning('Key {} not found in NIOS section.'.format(key))
                config[key] = ''
    else:
        logging.warning('No NIOS Section in config file: {}'.format(ini_filename))
        config['api_key'] = ''

    return config


def setup_logging(debug):
    '''
     Set up logging

     Parameters:
        debug (bool): True or False.

     Returns:
        None.

    '''
    # Set debug level
    if debug:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s %(levelname)s: %(message)s')

    return


def create_session(user: str = '',
                   passwd: str ='',
                   validate_cert: bool =False):
    '''
    Create request session

    Parameters:
    
    Return:
        wapi_session (obj): request session object
    '''
    headers = { 'content-type': "application/json" }

    # Avoid error due to a self-signed cert.
    if not validate_cert:
        requests.packages.urllib3.disable_warnings()
    
    wapi_session = requests.session()
    wapi_session.auth = (user, passwd)
    wapi_session.verify = validate_cert
    wapi_session.headers = headers

    return wapi_session


class DEVICES:
    '''
    Fixed Address Utility Class
    '''

    def __init__(self, cfg: str = 'gm.ini', page_size:int = 5) -> None:
        '''
        Init

        Parameters:
            cfg_file (str): Override default ini filename
        '''
        self.config:dict = {}
        self.config = read_ini(cfg)
        self.page_size = page_size

        self.gm = self.config.get('gm')
        self.wapi_version = self.config.get('api_version')
        self.username = self.config.get('user')
        self.password = self.config.get('pass')
        self.base_url = f'https://{self.gm}/wapi/{self.wapi_version}'
        self.devices = []
        self.networks = []
        self.not_in_ipam = []

        if self.config.get('valid_cert') == 'true':
            self.validate_cert = True
        else:
            self.validate_cert = False

        self.session = create_session( user=self.username,
                                      passwd=self.password,
                                      validate_cert=self.validate_cert)

        return
 

    def _add_params(self, url, first_param=True, **params):
        # Add params to API call URL
        if len(params):
            for param in params.keys():
               if first_param:
                   url = url + '?'
                   first_param = False
               else:
                   url = url + '&'
               url = url + param + '=' + params[param]
        
        return url


    def wapi_get(self, **params):
        '''
        Make wapi call

        Parameters:
            **params: parameters for request.get
        
        Returns:
            data: JSON response as object (list/dict) or None
        '''
        status_codes_ok = [ 200, 201 ]

        response = self.session.get(**params)
        if response.status_code in status_codes_ok:
            data = response.json()
        else:
            logging.error(f'HTTP response: {response.status_code}')
            logging.debug(f'Body: {response.content}')
            data = None

        return data


    def wapi_post(self, **params):
        '''
        Make wapi call

        Parameters:
            **params: parameters for request.post
        
        Returns:
            data: JSON response as object (list/dict) or None
        '''
        status_codes_ok = [ 200, 201 ]

        response = self.session.post(**params)
        if response.status_code in status_codes_ok:
            data = response.text
        else:
            logging.error(f'wapi_post failed: {response.status_code}, {response.content}')
            logging.debug(f'HTTP response: {response.status_code}')
            logging.debug(f'Body: {response.content}')
            data = None

        return data


    def wapi_put(self, **params):
        '''
        Make wapi call

        Parameters:
            **params: parameters for request.put
        
        Returns:
            data: JSON response as object (list/dict) or None
        '''
        status_codes_ok = [ 200, 201 ]

        response = self.session.put(**params)
        if response.status_code in status_codes_ok:
            data = response.text
        else:
            logging.error(f'wapi_post failed: {response.status_code}, {response.content}')
            logging.debug(f'HTTP response: {response.status_code}')
            logging.debug(f'Body: {response.content}')
            data = None

        return data


    def get_devices(self, next_page: str ='', **params) -> list:
        '''
        Get list of discovered devices

        Parameters:

        Returns:
            List of discovered devices
        '''
        devices:list = []
        count:int = 1
        page_err:bool = False
        return_fields:str = ( '_return_fields=address,name,network_view,extattrs,' +
                          'network_infos')
        paging:str = f'_paging=1&_max_results={self.page_size}&_return_as_object=1'
        url:str = f'{self.base_url}/discovery:device?{paging}&{return_fields}'

        # Get Devices
        if params:
            url = self._add_params(url, first_param=False, **params)

        # Use base session
        logging.info(f'Retrieving discovered devices')
        response = self.wapi_get(url=url)
        if response:
            logging.info(f'Page {count} retrieved successfully')
            logging.debug(f'Response: {response}')
            devices += (response.get('result'))
            next_page = response.get('next_page_id')
            # Page through data
            while next_page:
                count += 1
                logging.debug('Getting next page')
                url = f'{self.base_url}/discovery:device?{paging}&{return_fields}'
                url = self._add_params(url, first_param=False, _page_id=next_page )
                response = self.wapi_get(url=url)
                if response:
                    logging.info(f'Page {count} retrieved successfully')
                    # logging.debug(f'Response: {response}')
                    devices += response.get('result')
                    next_page = response.get('next_page_id')
                    logging.debug(f'Response: {next_page}')
                else:
                    logging.error(f'Failed to retrieve page {count}')
                    logging.debug(f'Response: {response}')
                    next_page = None
                    page_err = True
            if not page_err:
                logging.info('Complete: no more data pages.')
            else:
                logging.info('Error Occured: Returning retrieved devices')

        else:
            logging.error('Failed to retrieve discovered devices')
            devices = []
        
        self.devices = devices
        
        return self.devices


    def discovered_networks(self) -> list:
        '''
        Check whether networks are in IPAM and build list if not

        Parameters:
        Returns:
            updated list of networks not in ipam
        '''
        networks: list = []

        # Check whether we have the fixed addresses
        if not self.devices:
            self.get_devices()
        
        # Re-check
        if self.devices:
            for  device in self.devices:
                # Check for network_infos
                nets = device.get('network_infos')
                if nets:
                    logging.info('Discovered networks found')
                    for net in nets:
                        if net.get('network'):
                            in_ipam = True
                        else:
                            in_ipam = False

                        networks.append({ 'network': net.get('network_str'),
                                          'device': device.get('name'), 
                                          'in_ipam': in_ipam })

                else:
                        logging.debug(f'No networks found')

            self.networks = networks

        return networks


    def check_in_ipam(self) -> list:
        '''
        Check whether networks are in IPAM and build list if not

        Parameters:
        Returns:
            updated list of networks not in ipam
        '''
        not_in_ipam: list = []

        # Check whether we have the fixed addresses
        if not self.networks:
            self.discovered_networks()
        
        # Re-check
        # Check for network_infos
        for net in self.networks:
            if not net.get('in_ipam'):
                not_in_ipam.append({ 'network': net.get('network'),
                                     'device': net.get('device'),
                                     'in_ipam': False })
                logging.debug(f'Found network without ipam reference')


        return not_in_ipam


    def report(self, file=sys.stdout, 
                     format:str ='csv',
                     not_in_ipam:bool =False) -> None:
        '''
        Simple Report

        Parameters:
            file: filehandler = File handler obj or sys.stdout by default
            format: str = ['csv', 'table' or data dump]
            match_use: str = Use type to report on or all
        
        Note: file is only used for CSV output
        '''
        line: str = ''
        header: list = [ 'network', 'discovered device name', 'in_ipam' ]

        if not_in_ipam:
            if not self.not_in_ipam:
                net_report = self.check_in_ipam()
            else:
                net_report = self.not_in_ipam
        else:
            header: list = [ 'network', 'discovered device name', 'in_ipam' ]
            
            if not self.networks:
                net_report = self.discovered_networks()
            else:
                net_report = self.networks


        if format == 'csv':
            # Output in CSV format to file (or sys.stdout)
            try:
                w = csv.writer(file)
                w.writerow(header)

                for net in net_report:
                    line = ''
                    line = [ net.get('network'),
                             net.get('device'),
                             str(net.get('in_ipam')) ]
                    w.writerow(line)

            except Exception as err:
                logging.error(f'Error occured writing CSV: {err}')
                raise

        elif format == 'table':
            # Print a 'rich' table
            console = Console()

            # Create table and add columns
            table = Table()
            for h in header:
                table.add_column(h)

            # Add table rows
            for net in net_report:
                line = ''
                line = [ net.get('network'),
                         net.get('device'),
                         str(net.get('in_ipam')) ]
                table.add_row(*line)    
            
            # Print it!
            console.print(table)

        else:
            # Just print the data
            print(header)
            for net in not_in_ipam:
                line = ''
                line = [ net.get('network'),
                        net.get('device') ]
                print(line)

        return
    

def main():
    '''
    Code logic
    '''
    exitcode = 0
    run_time = 0

    # Parse CLI arguments
    args = parseargs()
    setup_logging(args.debug)

    t1 = time.perf_counter()

    disc_devs = DEVICES(cfg=args.config, page_size=args.page)

    # Output report
    if args.file:
        disc_devs.report(file=args.file, 
                         format='csv', 
                         not_in_ipam=args.not_in_ipam)
    else:
        disc_devs.report(format=args.format, not_in_ipam=args.not_in_ipam)
        

    run_time = time.perf_counter() - t1
    
    logging.info('Run time: {}'.format(run_time))

    return exitcode


### Main ###
if __name__ == '__main__':
    exitcode = main()
    exit(exitcode)
## End Main ###
