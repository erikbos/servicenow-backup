#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This script makes backups of tables of a ServiceNow instance. Dumps are
stored as is in XML-format to ensure they can be imported back into a
ServiceNow instance.
"""

from __future__ import print_function
import os
import io
import sys
import argparse
import requests
import csv
import gzip
from configobj import ConfigObj
from time import strftime
from lxml import etree

# todo:
# - check if XML rowcount limit is high enough to get all rows
# - get list of available tables from ServiceNow
# - check servicenow credentials
# - validate table response actually contains a table


def convert_xml_to_csv(xmlfilename, usedisplayvalue):
    """Converts a ServiceNow XML table dump to a CSV file. Column names are
    extracted from inputfile. Field values are as is or the display value
    can be used if present.
    """

    rowcount = 0
    firstline = True

    try:
        # should we open this as gzip file or not?
        # Set output file name based upon source filename
        if xmlfilename.endswith('.gz'):
            inputfile = gzip.open(xmlfilename, 'r')
            csvfilename = xmlfilename.rsplit('.', 2)[0] + '.csv'
        else:
            inputfile = open(xmlfilename, 'r')
            csvfilename = xmlfilename.rsplit('.', 1)[0] + '.csv'

        content = inputfile.read()
        context = etree.iterparse(io.BytesIO(content), events=('start', 'end'))

        # parse events of traversing the XML tree
        for event, elem in context:
            if event == 'start':
                # the unload tag has the data dump date
                if elem.tag == 'unload':
                    # data_dump_date = elem.attrib['unload_date']
                    continue

                # found a new row with data, get table name and get rid of
                # previous' row data
                if elem.getparent().tag == 'unload':
                    tablename = elem.tag
                    rowvalues = {}
                    rowheader = []
                    rowcount += 1
                    continue

                # in case of first row of values build up a list of column
                # names for this CSV
                if firstline:
                    rowheader.append(elem.tag)

                # store column values so they can be printed as
                # complete CSV row later on
                if usedisplayvalue and 'display_value' in elem.attrib and elem.attrib['display_value'] != '':
                    rowvalues[elem.tag] = elem.attrib['display_value']
                elif elem.text is not None:
                    rowvalues[elem.tag] = elem.text.encode('utf-8')

            # end of the input line: write row values as line to csv file
            elif event == 'end':
                # closing tag means we are at the end of the file
                if elem.tag == 'unload':
                    break
                # end of row
                elif elem.tag == tablename:
                    # in case of first line open the CSV and write header
                    # line with column names
                    if firstline:
                        print('Opening: ', csvfilename)

                        csvfile = open(csvfilename, 'w')
                        csvwriter = csv.DictWriter(csvfile, fieldnames=rowheader, lineterminator='\n')
                        csvwriter.writeheader()

                        firstline = False

                    # or write the row values and cleanup
                    else:
                        csvwriter.writerow(rowvalues)
                        rowvalues = {}
                        rowheader = []

            # remove parsed elements from memory
            elem.clear()

    except IOError as err:
        print("I/O error({0}): {1}".format(err.errno, err.strerror))

    finally:
        if csvfile:
            csvfile.close()
        print('Parsed', rowcount, 'rows in file', xmlfilename)


def download_table_as_xml(table_to_download, timestamp):
    """Download a ServiceNow table as XML and stores the content unmodified
    in a local file.
    """

    if timestamp:
        outfilename = table_to_download + ' ' + strftime("%Y-%m-%d %H:%M:%S") + '.xml.gz'
    else:
        outfilename = table_to_download + '.xml.gz'

    try:
        with gzip.open(outfilename, 'wb') as outputfile:
            # API endpoint
            url = 'https://' + config['instance'] + '/' + table_to_download + '.do?XML&useUnloadFormat=true'

            headers = {'Accept': 'application/xhtml+xml, application/xml'}
            response = requests.get(url, headers=headers, auth=(config['username'], config['password']))

            if response.status_code == 401:
                raise NameError('Authorization denied (401) by SN instance')

            if response.status_code != 200 or response.headers['content-type'] != 'text/xml':
                raise NameError('Wrong http response (' + str(response.status_code) + ') from SN instance')

            outputfile.write(response.content)
            outputfile.close()

    except requests.exceptions.RequestException as err:
        print('Unable to connect to SN instance: ', err)
        sys.exit(1)
    except IOError as err:
        print('I/O error({}): {}'.format(err.errno, err.strerror))
        sys.exit(1)
    except NameError as err:
        print(err)
        sys.exit(1)

TABLES = 'cmdb_ci_storage_server,u_cmdb_ci_wan,cmdb_rel_ci,sys_user'

parser = argparse.ArgumentParser(description='Backup tables from ServiceNow instance.')
parser.add_argument('-b', '--backup', help='Backup tables from instance', type=str, nargs='?', const=TABLES)
parser.add_argument('--timestamp', help='Put timestamp in backup filename', dest='timestamp', action='store_true')
parser.add_argument('--notimestamp', help='Do not put timestamp in backup filename', dest='timestamp', action='store_false')
parser.set_defaults(timestamp=True)
parser.add_argument('-c', '--convert', help='Convert table dump file(s) from XML to CSV', nargs='+')
parser.add_argument('-d', '--displayvalue', help='Use display value instead of sysid in CSV file', action='store_true')
parser.add_argument('-v', '--verbosity', type=int, choices=[0, 1, 2], help="Enable debugging", default=0)
args = parser.parse_args()

configFilePath = 'servicenow-backup.config'
config = ConfigObj(configFilePath)

if not args.backup and not args.convert:
    parser.print_help()
    sys.exit(1)

if args.convert:
    for filename in args.convert:
        print('Converting', filename)
        convert_xml_to_csv(filename, args.displayvalue)

if args.backup:
    if 'instance' not in config or 'username' not in config or 'password' not in config:
        print('Please ensure settings are available in ', configFilePath)
        sys.exit(1)

    backupdirectory = 'snbackup_' + config['instance'] + '_' + strftime("%Y-%m-%d %H:%M:%S")
    os.mkdir(backupdirectory)
    os.chdir(backupdirectory)

    for table in args.backup.split(','):
        download_table_as_xml(table, args.timestamp)
