import time

import datetime

from dateutil.tz import tzutc

def datetime_to_timestamp(dt):
    return time.mktime(dt.timetuple())

def timestamp_to_datetime(timestamp):
    return datetime.datetime.utcfromtimestamp(timestamp).replace(tzinfo=tzutc())

def now_timestamp():
    return time.time()

def now_datetime():
    return timestamp_to_datetime(now_timestamp())

def today_datetime():
    now_dt = now_datetime()
    return datetime.datetime(now_dt.year, now_dt.month, now_dt.day, tzinfo=tzutc())

def tomorrow_datetime():
    return (today_datetime() + datetime.timedelta(days=1))

def yesterday_datetime():
    return (today_datetime() - datetime.timedelta(days=1))

def today_timestamp():
    return datetime_to_timestamp(today_datetime())

def yesterday_timestamp():
    return datetime_to_timestamp(yesterday_datetime())

def tomorrow_timestamp():
    return datetime_to_timestamp(tomorrow_datetime())

def datetime_to_date_str(dt):
    return dt.strftime("%Y-%m-%d")

def three_days_prior(dt):
    return (dt - datetime.timedelta(days=3))

