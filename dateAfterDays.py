#!/usr/bin/python3
import datetime,sys
nbdays = int(sys.argv[1])
datetime.datetime.now().date()
newDate = datetime.datetime.now().date()+datetime.timedelta(days=nbdays)
print(newDate.strftime('%Y %b %d'))
