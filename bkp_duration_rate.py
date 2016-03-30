#!/usr/bin/python
#Author: Samir Ahmed
#Date: 16/1/2016
#Purpose: collect backup statistics like client name, savesets, start time, end time..etc. and add durations, and backup backup rate.

import sys, os, re
import time
import datetime as dt
import logging
#logging.disable (logging.CRITICAL)
logging.basicConfig(filename="output.log", level=logging.DEBUG, format=' %(asctime)s - %(levelname)s - %(message)s')
logging.debug('Start of %s..' % (sys.argv[0]))

#add the backup server name/IP
backup_server = "BKP_SERVER"

def last_bkp (CName, stime, etime): 
	bkp_day_start = stime + " 00:00"
	bkp_day_end = etime + " 23:59"
	logging.debug('client name: %s, day start: %s, day end: %s' % (CName, bkp_day_start, bkp_day_end))
	size = 0
	CName_file = CName + "_bkp_details"
	os.system ('mminfo -s %s -c %s -q "savetime >= %s, savetime <= %s" -r "client, name, nfiles, sumsize, level, sscreate (23), sscomp (23)" -ot | sed -e \'1d\' | uniq > %s' % (backup_server, CName, bkp_day_start, bkp_day_end, CName_file))
	fd = open (CName_file, 'r')
	print ("Client SaveSet NFiles Size(MB) Start_Time End_Time Level Duration TotalDuration(sec) Rate(MB/s)")
	for i in fd:
		logging.debug('i: %s' % (i))
		duration_sec = 1
		duration_hours = 0
		duration_minutes = 0
		duration_seconds = 0
		m = re.search (r'''([\w]+)				#Client Name m.group(1)
				([-.\w]*?)\s+				#suffix m.group(2)
				([\\:?\w\/}{-]+[.\s\w:\\]*?)\s+
				(\d+)\s+(\d+)\s+(\w+)\s+
				(\w+)\s+
				(\d+/\d+/\d+\s\d+:\d+:\d+)\s+
				([A|P]M)\s+
				(\d+/\d+/\d+\s\d+:\d+:\d+)\s+
				([A|P]M)
				''', i, re.X)
		for x in range(1, 12):	
			logging.debug('m.group(%d): %s' % (x, m.group(x)))
		epoc_start = int (time.mktime(time.strptime(m.group (8) + " " +  m.group(9), "%m/%d/%Y %I:%M:%S %p")))
		epoc_end = int (time.mktime(time.strptime(m.group (10) + " " + m.group(11), "%m/%d/%Y %I:%M:%S %p")))
		logging.debug('%s\nepoc_start: %d\nepoc_end: %d' % (m.group(3), epoc_start, epoc_end))
		if epoc_start != epoc_end:
			duration_sec = epoc_end - epoc_start
			duration_hours = int (duration_sec/(60*60))
			duration_hours_mod = duration_sec%(60*60)
			duration_minutes = duration_hours_mod/60
			logging.debug('duration_minutes: %d' % (duration_minutes))
			duration_seconds = duration_hours_mod%60
		if m.group(6) == 'GB':
			size = float (m.group (5)) * 1024
		elif m.group(6) == 'TB':
			size = float (m.group (5)) * 1024 * 1024
		elif m.group(6) == 'KB':
			size = float (m.group (5)) / 1024
		else:
			size = float (m.group (5))
		rate = float (round ((size/duration_sec), 3))
		Client = m.group(1)
		SaveSet = m.group(3)
		NFiles = int (m.group(4))
		Size = size
		Start_Time = m.group(8) + " " + m.group(9)
		End_Time = m.group(10) + " " + m.group(11)
		Level = m.group(7)
		Duration = str (duration_hours) + ":" + str (duration_minutes) + ":" + str (duration_seconds)
		TotalDuration = duration_sec
		Rate = rate
		print ("%s %s %d %d %s %s %s %s %d %.3f" % (Client, SaveSet, NFiles, Size, Start_Time, End_Time, Level, Duration, TotalDuration, Rate))
	fd.close ()
	os.unlink (CName_file)
	return

if __name__ == '__main__':
	if len (sys.argv) != 4:
		print "Usage: ", sys.argv[0], "ClientName", "StartDATE(m/d/y)", "EndDATE(m/d/y)"
		sys.exit (1)
	client_name = sys.argv[1]
	stime = sys.argv[2]
	etime = sys.argv[3]
	last_bkp (client_name, stime, etime)
