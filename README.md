### servicenow-backup

## Summary

This script can be used to make backups of tables of a ServiceNow instance 
outside ServiceNow. Dumps are stored as is in XML-format to ensure they can be 
imported back into an instance.

Table XML files can also be converted using this script to CSV so a table can
read in

## Motivation

It can be useful to have an archive of dump tables available. Some companies
might want to have a copy of their data available outside of ServiceNow for
legal, business or other reasons. 

## Archiving to AWS

To archive your data you could consider using:
* [https://github.com/clarete/s3sync] to archive datasets into AWS S3 or Glacier.

## ServiceNow instance preparation

Create a user in your ServiceNow instance that has access to the tables that you
want to backup.

**You need to ensure that this user has access to all rows and all columns. If not
your table dump files will be incomplete** !

Put the hostname of your instance and the backup user name and password in 
servicenow-backup.config.

## Usage

Backup:

    $ servicenow-backup -b

Converting one or more table files from XML to CSV:

	$ servicenow-backup -c filename (filename)

	Use -d to use a field's displayname instead of sysid when convert to CSV.
