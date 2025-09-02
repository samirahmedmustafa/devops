#!/opt/rh/python33/root/usr/bin/python3

import sys, os
import re
import subprocess
import json
import logging
import openpyxl
from openpyxl.styles import *
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.marker import DataPoint
import smtplib
from email.mime.text import MIMEText
logging.disable (logging.CRITICAL)

logging.basicConfig(filename='vplex_fetch.log', level=logging.DEBUG, format=' %(asctime)s - %(levelname)s - %(message)s')
logging.debug('Start of %s' % (sys.argv[0]))

USERNAME = [service user]
PASSWORD = [service password]
VPLEX_IP = [ip address]
EMAIL_FROM = [storage email]
EMAIL_TO = [team email]

def st_view (clusName):
	cmd = "curl -k -H \"Username:" + USERNAME + "\" -H \"Password:" + PASSWORD + "\" -s -g -d \'{\"args\":\"/clusters/" + clusName + "/exports/storage-views/\"}\' -X POST https://" + VPLEX_IP + "/vplex/ls"
	sv_list = []
	output = json.loads (str ((subprocess.check_output (cmd, shell=True)).decode ("utf-8")))
	l = (((output['response'])['custom-data'])).split ()
	for i in l:
		if i != '/clusters/' + clusName + '/exports/storage-views:':
			sv_list.append (i)
	return (sv_list)

def view_show (view_name, clusName):
	r = []
	cmd = "curl -k -H \"Username:" + USERNAME + "\" -H \"Password:" + PASSWORD + "\" -s -g -d \'{\"args\":\"-lf /clusters/" + clusName + "/exports/storage-views/" + view_name + "\"}\' -X POST https://" + VPLEX_IP + "/vplex/ls"
	output = json.loads (str ((subprocess.check_output (cmd, shell=True)).decode ("utf-8")))
	l = (((output['response'])['custom-data'])).split ()
	for i in l:
		if (re.search (r'\(.*\)', i)):
			r.append (((re.sub ('\[|\]|\(|\)|[,]$', '', i))).split (','))
	return (r)

def st_calc (sv_dict, view_name):
	total = 0
	num = 0
	size = ''
	for i, j, l, m in sv_dict[view_name]:
		num = float (re.search (r'(\d*.\d*)(G|T|P)', m).group (1))
		size = re.search (r'(\d*.\d*)(G|T|P)', m).group (2)
		if size == 'G':
			num = num * 1
		elif size == 'T':
			num = num * 1024
		elif size == 'P':
			num = num * (1024 ** 2)
		total = total + num 
	sv_dict [view_name].append (['Total', '', '', format (total, '.2f')])
	return sv_dict

def pop_excl (sv_dict, ClusName):
	wb = openpyxl.Workbook ()
	sh = wb.active		
	count1 = 0
	count2 = 2
	alph = ['a', 'b', 'c', 'd']
	f = sh['a1'] 
	f.font = Font (bold=True)
	f = sh['b1'] 
	f.font = Font (bold=True)
	sh.title = 'HighLevel'
	sh['a1'] = 'StorageView'
	sh['b1'] = 'Size(G)'
	for i in sv_dict:
		sh[alph[count1] + str (count2)] = i
		count1 += 1
		sh[alph[count1] + str (count2)] = float (sv_dict[i][-1][-1])
		count2 += 1
		count1 = 0
	count2 = 2
	for i in sv_dict:
		sh = wb.create_sheet (i)		
		sh = wb.get_sheet_by_name (i)
		f = sh['a1']
		f.font = Font (bold=True)
		f = sh['b1']
		f.font = Font (bold=True)
		f = sh['c1']
		f.font = Font (bold=True)
		f = sh['d1']
		f.font = Font (bold=True)
		sh['a1'] = 'LunID'
		sh['b1'] = 'Name'
		sh['c1'] = 'VPD'
		sh['d1'] = 'Size(G/T)'
		for j in range (len (sv_dict[i])):
			for k in range (4):
				sh[alph[count1] + str (count2)] = sv_dict[i][j][k]
				count1 += 1
			count2 += 1
			count1 = 0
		count2 = 2

	logging.debug('Start of chart')
	l = len(sv_dict)

	sh = wb.get_sheet_by_name ('HighLevel')
	logging.debug('sheets: %s' % (wb.get_sheet_names ()))
	logging.debug('sh: %s' % (sh.title))
	chart1 = BarChart()
	chart1.type = "col"
	chart1.style = 11
	chart1.title = "VPlex Capacity Report"
	chart1.y_axis.title = 'Size'
	chart1.x_axis.title = 'View Name'
	logging.debug('len of sv_dict: %d' % (l))
	data = Reference(sh, min_col=2, min_row=2, max_row=l + 1, max_col=2)
	cats = Reference(sh, min_col=1, min_row=2, max_row=l + 1)
	chart1.add_data(data, titles_from_data=False)
	chart1.set_categories(cats)
	chart1.top = 100
	chart1.left = 30
	chart1.width = 27
	chart1.height = 10
	chart1.shape = sh.add_chart(chart1, "D2")

	wb.save (ClusName)
	return 0
	
def main ():
	c_tup = ('cluster-1', 'cluster-2')
	clus_dict = {}
	sv_dict1 = {}
	sv_dict2 = {}
	sv_list = []
	for i in st_view ('cluster-1'):
		logging.debug('cluster-1 start view name: %s' % (i))
		for j in (view_show (i, 'cluster-1')):
			sv_list.append (j)
		sv_dict1[i] = sv_list
		sv_dict1[i] = st_calc (sv_dict1, i)[i]
		sv_list = []
	
	pop_excl (sv_dict1, 'VPlexReport_Cluster1.xlsx')

	for i in st_view ('cluster-2'):
		logging.debug('cluster-2 start view name: %s' % (i))
		for j in (view_show (i, 'cluster-2')):
			sv_list.append (j)
		sv_dict2[i] = sv_list
		sv_dict2[i] = st_calc (sv_dict2, i)[i]
		sv_list = []
	pop_excl (sv_dict2, 'VPlexReport_Cluster2.xlsx')

	os.system ('echo "VPlex Report" | /bin/mailx -s "VPlex Report" -r %s -a VPlexReport_Cluster1.xlsx -a VPlexReport_Cluster2.xlsx %s' % (EMAIL_FROM, EMAIL_TO))
	logging.debug('end of script')
	
	return 0
if __name__ == '__main__':
	main ()
