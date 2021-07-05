import sys
import aiohttp
import asyncio
import csv
import time
import re

from bs4 import BeautifulSoup
from datetime import datetime
from aiohttp_socks import ProxyConnector as pc

'''
	Goes through a list of provided urls in csv, gets the titles, and outputs them in another csv.

	TODO:
		Might need to move the csv writer out of the aiohttp session context in the main function.
'''

# gets the pages
async def runner(url, hits, session):
	# set up dict to contain page info
	response = {}
	response['url'] = url.strip()
	response['hits'] = hits
	response['timestamp'] = (datetime.now()).strftime("%m/%d/%Y %H:%M:%S")

	try:
		# get the page
		async with session.get(url.strip(), timeout=20) as r:
			text = await r.content.read(-1)
			status = r.status

		# parse title
		soup = BeautifulSoup(text, 'lxml')

		if soup.title:
			response['title'] = re.sub(r'\W+', ' ', soup.title.string)
		else:
			response['title'] = "no title"

		response['status'] = str(status)

	except Exception as e:
		print("runner exception: " + str(e))
		response['title'] = "N/A"
		response['status'] = '-1'

	# returns dict after trycatch
	return response


async def initiate(innie,outie,header):
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
	connector = pc.from_url(proxy)
	
	# Spin off runners to get pages
	async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
		tasks = []
		for url in in_reader:
			task = asyncio.create_task(runner(url[0], url[1], session))
			tasks.append(task)
		
		# gather the runners when they return
		results = await asyncio.gather(*tasks)

		# put the results the outfile. if it cant write, try encoding the title as utf-8.
		for result in results:
			try:
				out_writer.writerow([result['url'], result['status'], result['hits'], results['timestamps'], results['title']])
			except Exception:
				out_writer.writerow([result['url'], result['status'], result['hits'], results['timestamps'], (results['title']).encoding('utf-8')])

# this method triggers initiate
def proccess_links(innie,outie,header):
	# timer for testing
	start_time = time.time()

	# workaround for selector loop selection bug in windows
	if sys.version_info[0] == 3 and sys.version_info[1] >= 8 and sys.platform.startswith('win'):
		asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

	# start the async with debug enabled for extra dubug logs
	asyncio.run(initiate(innie,outie,header), debug=True)

	# end the timer
	print("--- %s seconds ---" % (time.time() - start_time))