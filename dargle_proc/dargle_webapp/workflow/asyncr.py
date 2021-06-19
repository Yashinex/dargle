import aiohttp
import asyncio
import csv
import time

from bs4 import BeautifulSoup
from datetime import datetime
from aiohttp_socks import ProxyConnector as pc

# gets the pages
async def runner(url, hits, session):
	# set up dict to contain page info
	response = {}
	response['url'] = url.strip()
	response['hits'] = hits

	try:
		# get the page
		async with session.get(url, timeout=20) as r:
			text = await r.content.read(-1)
			status = r.status

		# parse title
		soup = BeautifulSoup(text, 'lxml')
		response['title'] = soup.title.string

		response['status'] = status

	except Exception as e:
		print("runner exception: " + str(e))

	response['timestamp'] = (datetime.now()).strftime("%m/%d/%Y %H:%M:%S")

	# returns dict
	return response


async def main(innie,outie,header):
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
	async with aiohttp.ClientSession(connector=connector) as session:
		tasks = []
		for url in in_reader:
			task = asyncio.create_task(runner(url[0], url[1], session))
			tasks.append(task)
		
		# gather the runners when they return
		results = await asyncio.gather(*tasks)

		# put the results the outfile
		for result in results:
			out_writer.writerow([result['url'], result['status'], result['hits'], results['timestamps'], results['title']])


# this method triggers main
def proccess_links(innie,outie,header):
	# timer for testing
	start_time = time.time()

	# patches selector loop selection bug
	asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
	# start the async with debug enabled
	asyncio.run(main(innie,outie,header), debug=True)

	# end the timer
	print("--- %s seconds ---" % (time.time() - start_time))