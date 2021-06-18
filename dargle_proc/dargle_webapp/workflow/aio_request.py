import aiohttp
import asyncio
import csv
import time
import sys

import traceback

from bs4 import BeautifulSoup
from datetime import datetime
from aiohttp_socks import ProxyConnector
import python_socks


# the reading head
async def get_page(url, hits, session, sem):

    # make sure the url has http:// on it
    if (url[0:4] != 'http'):
        url = 'http://' + url
    # clean up any whitespace or newlines
    url = url.rstrip('\n')

    # response dictonary
    ret = {}
    ret['url'] = url
    ret['timestamp'] = (datetime.now()).strftime("%m/%d/%Y %H:%M:%S")
    ret['hits'] = int(hits)

    # setup retry variables
    max_retries = 2
    timeout = 16

    # main request retry loop
    for attempt in range(max_retries):

        # change the timeout on retries
        if attempt != 0:
            timeout = 20
        try:
            start_req = time.time()

            # the actual request
            async with sem, session.get(url, timeout=timeout, allow_redirects=True, max_redirects=10) as r:

                # dictating the output encoding helps tremendusly with preformance
                text = await r.text(encoding='utf-8')

                # load everything you want into dict
                ret['request_time'] = (time.time() - start_req)
                ret['title'] = (await parse_for_title(text))
                ret['status'] = r.status

                if r.history is not None:
                    ret['redirects'] = r.history
                
                
                return ret

        # start of exceptions
        except asyncio.TimeoutError as e:
            # this is just for visual help with retries
            print("++++++++++++++++++++++ timeout wait: " +
                  str(timeout) + "   " + url)

            # when max retries reached
            if attempt == max_retries:
                ret['request_time'] = (time.time() - start_req)
                if len(str(e)) == 0:
                    ret['error'] = "client timeout"
                else:
                    ret['error'] = str(e)

                return ret

            # pause before trying again
            await asyncio.sleep(1)

        # handles proxy errors, namely falure to resolve names
        except python_socks.ProxyError as e:
            if len(str(e)) == 0:
                ret['error'] = "proxy error"
            else:
                ret['error'] = "proxy error " + str(e)
            return ret

        except UnicodeDecodeError as e:
            if len(str(e)) == 0:
                ret['error'] = "can not decode with utf-8"
            else:
                ret['error'] = str(e)

            return ret

        except Exception as e:
            if len(str(e)) == 0:
                ret['error'] = "A general exception ocurred in get_page()"
            else:
                ret['error'] = str(e)

            return ret


# it parses the text of the request as html and returns the title in utf-8
async def parse_for_title(text):
    try:
        # parse the html.  skip encoding detection as it is known utf-8
        soup = BeautifulSoup(text, "lxml")

        # get the title
        title = soup.title

        # if there is a title, encoded it.  if not, return error msg
        if title is not None:
            title = soup.title.string.encode('utf-8')
        else:
            title = "b4 err: no title on this page"

        return title
    except Exception as e:
        err_msg = "+++++++++ b4 err: " + str(e)
        print(err_msg)

        return err_msg


def write_out(results, outie):
    # write the results to file
    avg_time = 0
    errors = 0
    redirects = 0 
    timeouts = 0
    dns_fail = 0

    try:
        writer = csv.writer(open(outie, 'w+', newline=''))

        for ret in results:

            if ret is not None and ret != 'None':
                if 'error' in ret:
                    writer.writerow([ret['url'], ret['error'],ret['hits'], ret['timestamp'], "N/A"])

                    if ret['error'] == 'timeout':
                        timeouts += 1

                    if 'proxy error' in ret['error']:
                        dns_fail += 1

                    errors += 1
                else:
                    writer.writerow(
                        [ret['url'], ret['status'], ret['hits'], ret['timestamp'], ret['title']])

                    avg_time += ret['request_time']
            else:
                writer.writerow(["NONE  was the returned value for this task", "n/a", 0, "n/a", "n/a"])
                errors += 1

    except Exception as e:
        print(traceback.print_exc())
        print("Error in writing outfile: " + str(e))

    print("======= stats ========")
    print("errors: " + str(errors))
    print("average request time: " + str(avg_time / (len(results) - errors + 0.1)))
    print("redirects: " + str(redirects))
    print("timeouts: " + str(timeouts))
    print("dns falure: " + str(dns_fail))


# the main working async function
async def main(innie, outie, header):

    # setup the csv file to be read from
    infile = open(innie, 'r')
    in_reader = csv.reader(infile, delimiter=',')
    if header == 'true':
        next(in_reader, None)

    # max number of sessions open
    sem = asyncio.Semaphore(400)

    # http headers
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
    }

    # proxy
    proxy = "socks5://localhost:9050"
    connector = ProxyConnector.from_url(proxy)

    # set up the session
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        # this is the complicated part.  makes a buncha "sessions" named tasks and then collects them at the end.
        tasks = []
        for row in in_reader:
            task = asyncio.create_task(get_page(row[0], row[1], session, sem))
            tasks.append(task)

        # gather up the "sessions" and wait for them to all end
        results = await asyncio.gather(*tasks)

        # write the results to file
        write_out(results, outie)


# this is triggered by external proccess and kicks off the main async def up there ^^^^^^
def proccess_links(innie, outie, header):

    # count the lines in the file
    with open(innie) as f:
        for i, l in enumerate(f):
            pass
    f.close()
    print("Number of sites loaded: " + str(i+1))

    # start timer
    start_time = time.time()

    # windows bug workaround 'https://stackoverflow.com/a/66772242'
    if sys.version_info[0] == 3 and sys.version_info[1] >= 8 and sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # this sets up and takes down the working loop and stuff.  also handles closing "sessions" cause that is complicated apparently
    asyncio.run(main(innie, outie, header))

    # end the timer and print the time
    print("\n")
    print("runtime ----- %s seconds ---" % (time.time() - start_time))
