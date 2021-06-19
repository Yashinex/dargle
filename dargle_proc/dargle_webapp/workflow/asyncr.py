import aiohttp
import asyncio
import csv
import time
import sys

import traceback

from bs4 import BeautifulSoup
from datetime import datetime
from aiohttp_socks import ProxyConnector as pc
import python_socks

def process_links(innie,outie,header):
	infile = open(innie, 'r')
	outfile = open(outie, 'w+')

	# Read in CSV, skip header
	in_reader = csv.reader(infile, delimiter=',')
	out_writer = csv.writer(outfile)

	if header == 'true':
		next(in_reader, None)

	# User-agent header
	headers = {}
	headers['User-agent'] = "HotJava/1.1.2 FCS"

	# SOCKS Proxy
	proxy = "socks5://localhost:9050"
	connect = pc.from_url(proxy)