import aiohttp
import asyncio
import csv
import time

from bs4 import BeautifulSoup
from datetime import datetime
from aiohttp_socks import ProxyConnector


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
    ret['hits'] = hits

    # setup retry variables
    max_retries = 2
    timeout = 16

    # main request retry loop
    for attempt in range(max_retries):

        # change the timeout on retries
        if attempt != 0:
            timeout = 60
        try:
            start_req = time.time()

            # the actual request
            async with sem, session.get(url, timeout=timeout) as r:

                #dictating the output encoding helps tremendusly with preformance
                text = await r.text(encoding='utf-8')

                #load everything you want into dict
                ret['request_time'] = (time.time() - start_req)
                ret['title'] = (await parse_for_title(text))[2: -1]
                ret['status'] = r.status

                return ret


        # start of exceptions

        except asyncio.TimeoutError as e:
            # this is just for visual help with retries
            print("++++++++++++++++++++++ timeout wait: " + str(timeout) + "   " + url)

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

        except UnicodeDecodeError as e:

            ret['request_time'] = (time.time() - start_req)
            if len(str(e)) == 0:
                ret['error'] = "can not decode with utf-8"
            else:
                ret['error'] = str(e)

            return ret

        except Exception as e:

            ret['request_time'] = (time.time() - start_req)
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
    try:
        writer = csv.writer(open(outie, 'w+'))
        for ret in results:
            if ret is not None:
                if 'error' in ret:
                    writer.writerow([ret['url'],ret['error'],ret['hits'],ret['timestamp'],"N/A"])
                else:
                    writer.writerow([ret['url'],ret['status'],ret['hits'],ret['timestamp'],ret['title']])
            else:
                writer.writerow(["NONE"])
    except Exception as e:
        print("Error in writing outfile: " + str(e))


# the main working fucntion
async def main(innie,outie,header):

    # setup the csv file to be read from
    infile = open(innie, 'r')
    in_reader = csv.reader(infile, delimiter=',')
    if header == 'true':
        next(in_reader,None)

    # max number of sessions open
    sem = asyncio.Semaphore(400)

    #http headers
    headers = {
        "user-agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
    }

    #proxy
    proxy = "socks5://localhost:9050"
    connector = ProxyConnector.from_url(proxy)


    #set up the session
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        # this is the complicated part.  makes a buncha "sessions" named tasks and then collects them at the end.
        tasks = []
        for row in in_reader:
            task = asyncio.create_task(get_page(row[0], row[1], session, sem))
            tasks.append(task)

        # gather up the "sessions" and wait for them to all end
        results = await asyncio.gather(*tasks)

        #write the results to file
        write_out(results, outie)



# this is triggered by external proccess and kicks off the main async def
def proccess_links(innie,outie,header):

    # count the lines in the file
    with open(innie) as f:
        for i, l in enumerate(f):
            pass
    f.close()
    print("Number of sites loade: " + str(i+1))

    #start timer
    start_time = time.time()

    # windows bug workaround 'https://stackoverflow.com/a/66772242'
    #asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # this sets up and takes down the working loop and stuff.  also handles closing "sessions" cause that is complicated apparently
    asyncio.run(main(innie,outie,header))

    # end the timer and print the time
    print("\n\n\n")
    print("--- %s seconds ---" % (time.time() - start_time))




