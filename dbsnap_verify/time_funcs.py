from time import time

import datetime

def now_timestamp():
    return int(time())

def timestamp_to_datetime(timestamp):
    return datetime.datetime.fromtimestamp(timestamp)

def now_datetime():
    return datetime.datetime.now()

def today_date():
    return now_datetime()

def tomorrow_date():
    return(now_datetime() + datetime.timedelta(days=1))

def datetime_to_date_str(dt):
    return dt.strftime("%Y-%m-%d")

def date_str_to_datetime(date_str):
    return datetime.datetime(*map(int, date_str.split("-")))
