====================================
NIOS Discovered Devices and Networks
====================================

| Version: 0.0.9
| Author: Chris Marrison
| Email: chris@infoblox.com

Description
-----------

Provides a python script and class to assist with extracting discovered 
network information from NIOS and whether report on whether the networks,
associated device and whether the networks exist in IPAM or not.

Demonstration code is included that enables this to be used as a simple 
script.


Prerequisites
-------------

Python 3.10+


Installing Python
~~~~~~~~~~~~~~~~~

You can install the latest version of Python 3.x by downloading the appropriate
installer for your system from `python.org <https://python.org>`_.

.. note::

  If you are running MacOS Catalina (or later) Python 3 comes pre-installed.
  Previous versions only come with Python 2.x by default and you will therefore
  need to install Python 3 as above or via Homebrew, Ports, etc.

  By default the python command points to Python 2.x, you can check this using 
  the command::

    $ python -V

  To specifically run Python 3, use the command::

    $ python3


.. important::

  Mac users will need the xcode command line utilities installed to use pip3,
  etc. If you need to install these use the command::

    $ xcode-select --install

.. note::

  If you are installing Python on Windows, be sure to check the box to have 
  Python added to your PATH if the installer offers such an option 
  (it's normally off by default).


Modules
~~~~~~~

Non-standard modules:

    - rich (for pretty printing)

Complete list of modules::

  import logging
  import requests
  import argparse
  import configparser
  import time
  import sys
  import csv
  from rich import print
  from rich.console import Console
  from rich.table import Table


Installation
------------

The simplest way to install and maintain the tools is to clone this 
repository::

     git clone https://github.com/ccmarris/nios_discovered_networks


Alternative you can download as a Zip file.


Basic Configuration
-------------------

The script utilise a gm.ini file to specify the Grid Master, API version
and user/password credentials.


gm.ini
~~~~~~~

The *gm.ini* file is used by the scripts to define the details to connect to
to Grid Master. A sample inifile is provided and follows the following 
format::

  [NIOS]
  gm = '192.168.1.10'
  api_version = 'v2.12'
  valid_cert = 'false'
  user = 'admin'
  pass = 'infoblox'


You can use either an IP or hostname for the Grid Master. This inifile 
should be kept in a safe area of your filesystem. 

Use the --config/-c option to override the default ini file.


Usage
-----

The script supports -h or --help on the command line to access the options 
available::

  % ./nios_discovered_networks.py --help
  usage: nios_discovered_networks.py [-h] [-c CONFIG] [-f FILE] [-F FORMAT] [-n] [-p PAGE] [-d]

  NIOS Fixed Address Utility

  options:
    -h, --help            show this help message and exit
    -c CONFIG, --config CONFIG
                          Override ini file
    -f FILE, --file FILE  Output CSV to file
    -F FORMAT, --format FORMAT
                          Report display format [csv, table]
    -n, --not_in_ipam     Report only networks that are not in IPAM
    -p PAGE, --page PAGE  Page size to use for retrieving discovered devices
    -d, --debug           Enable debug messages


Examples
--------

Simple Report on Fixed Address::

  % ./nios_discovered_networks.py --config gm.ini 


Enable debug::

  % ./nios_discovered_networks.py --config gm.ini --debug


Report on networks that are not in IPAM only::

  % ./nios_discovered_networks.py --config gm.ini --not_in_ipam
  % ./nios_discovered_networks.py -c gm.ini -n


Output to file::

  % ./nios_discovered_networks.py --config gm.ini --file report.csv


Note
----

Although a simple API call, retrieving the discovered networks can return
a large amount of data per device and so this script uses a relatively small
page_size to page through the data (default=5). You can increase or decrease
the page size using the *--page* option. However, if you experience HTTP 
session timeouts you can further reduce the page size from the default, 
with a minimum value of 1 (i.e. one device per page).


License
-------

This project is licensed under the 2-Clause BSD License
- please see LICENSE file for details.


Aknowledgements
---------------


