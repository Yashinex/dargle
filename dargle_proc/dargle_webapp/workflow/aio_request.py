import aiohttp
import asyncio
import csv
import time

from bs4 import BeautifulSoup
from datetime import datetime


# the reading head
async def get_page(url, hits, session, sem):

    # make sure the url has http:// on it
    if (url[0:4] != 'http'):
        url = 'http://' + url
    
    # clean up any whitespace or newlines
    url = url.rstrip('\n')
    
    #proxy setup
    #TODO: setup proxy 'session.get(url, proxy=proxy)'
    proxy = "socks5h://localhost:9050"

    max_retries = 1
    timeout = 4

    for attempt in range(max_retries):
        if attempt != 0:
            timeout = pow(timeout, 2)
        try:
            async with sem, session.get(url, timeout=timeout, proxy=proxy) as r:

                #dictating the output encoding helps tremendusly with preformance
                text = await r.text(encoding='utf-8')

                title = await parce_for_title(text)
                timestamp = datetime.now()
                msg = ("{u},{s},{h},{t},{m}").format(u=url, s=str(r.status), h=hits,t=timestamp.strftime("%m/%d/%Y %H:%M:%S"), m=str(title)[2:-1])

                return msg
        except asyncio.TimeoutError as e:
            print("++++++++++++++++++++++ timeout wait: " + str(timeout) + "   " + url)
            
            # after the last retry, print error message
            if attempt == max_retries:
                timestamp = datetime.now()
                err_msg = ("{u},{s},{h},{t},{m}").format(u=url, s="timeout", h=hits,t=timestamp.strftime("%m/%d/%Y %H:%M:%S"), m="N/A")
                return err_msg

            #pause for a sec to not hammer server
            await asyncio.sleep(1)

        except Exception as e:
            timestamp = datetime.now()
            err_msg = ("{u},{s},{h},{t},{m}").format(u=url, s=str(e), h=hits,t=timestamp.strftime("%m/%d/%Y %H:%M:%S"), m="N/A")
            return err_msg


# this is a home made async method
# it parses the text of the request as html and returns the title in utf-8
async def parce_for_title(text):
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
        print("b4 err: " + str(e))


# the main working method.  it mainly just triggers the reading head and sets up stuff
async def main(innie,outie,header):

    # setup the csv file into dict format
    infile = open(innie, 'r')
    in_reader = csv.reader(infile, delimiter=',')
    if header == 'true':
        next(in_reader,None)

    # max number of sessions open
    sem = asyncio.Semaphore(200)
    # connection timeout
    timeout = aiohttp.ClientTimeout(total=15)
    #http headers
    headers = {
        "user-agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
    }
    #set up the session
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        # this is the complicated part.  makes a buncha "sessions" named tasks and then collects them at the end.
        # this triggers the reading head method at the top
        tasks = [
            # url, hits, session, sem, outfile
            asyncio.create_task(
                get_page(row[0], row[1], session, sem)
                )
                # the for loop is reading from the csv containing the urls.  the [0] is just where the url is in that format
                for row in in_reader
        ]

        # gather up the "sessions" and wait for them to all end
        results = await asyncio.gather(*tasks)

        try:
            with open(outie, 'a') as f:
                for line in results:
                    f.write(str(line))
                    f.write("\n")
        except Exception as e:
            print(str(e))



# this is triggered by external proccess and kicks off the main async def
# innie, outie, header
def proccess_links(innie,outie,header):

    # count the lines in the file
    with open(innie) as f:
        for i, l in enumerate(f):
            pass
    f.close()
    print(i+1)

    #start timer
    start_time = time.time()

    # windows bug workaround 'https://stackoverflow.com/a/66772242'
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # this sets up and takes down the working loop and stuff.  also handles closing "sessions" cause that is complicated apparently
    asyncio.run(main(innie,outie,header))

    # end the timer and print the time
    print("\n\n\n")
    print("--- %s seconds ---" % (time.time() - start_time))




