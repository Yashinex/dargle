import request, dargle_orm, sys, aio_request

innie = sys.argv[1]
outie = sys.argv[2]
# thread_num = int(sys.argv[3])
domain = sys.argv[3]
header = sys.argv[4]
check = sys.argv[5]

request.line_count(innie)

if check == 'true':
    #csv = request.process_links(innie,outie,header)

    # uncomment for async version of requests
    csv = aio_request.proccess_links(innie,outie,header)

    
# For troubleshooting/skipping requests
else:
    csv = outie
dargle_orm.dbUpdate(csv,domain)
