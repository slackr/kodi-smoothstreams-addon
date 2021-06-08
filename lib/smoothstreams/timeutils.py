# -*- coding: utf-8 -*-
#
# With modified code originally by spline
from __future__ import absolute_import, division, unicode_literals
from .compat import datetime, timedelta_total_seconds
import time
import pytz
from . import tzlocal
import calendar

LOCAL_TIMEZONE = None
TIMEZONE_OFFSET = 0

def setLocalTimezone(from_offset=None):
	utc_time = datetime.datetime.now(pytz.utc).replace(microsecond=0, second=0).timetuple()
	local_time = pytz.utc.localize(datetime.datetime.today(), is_dst=None).replace(microsecond=0, second=0).timetuple()
	global LOCAL_TIMEZONE
	global TIMEZONE_OFFSET
	if from_offset is not None:
		if from_offset == 0:
			LOCAL_TIMEZONE = pytz.UTC
		else:
			LOCAL_TIMEZONE = pytz.FixedOffset(from_offset)
	else:
		try:
			delta_mins = int((time.mktime(local_time) - time.mktime(utc_time)) / 60)
			LOCAL_TIMEZONE = pytz.FixedOffset(delta_mins)
		except Exception as e:
			try:
				from dateutil.tz import tzlocal
				LOCAL_TIMEZONE = pytz.UTC
			except Exception as e:
				from compat import timezone_guess
				LOCAL_TIMEZONE = timezone_guess(int(timedelta_total_seconds(datetime.datetime.now() - datetime.datetime.utcnow())))

	TIMEZONE_OFFSET = int(round(time.mktime(datetime.datetime.now(tz=LOCAL_TIMEZONE).replace(microsecond=0, second=0).timetuple()) - time.mktime(utc_time)))

setLocalTimezone()

UTC_EPOCH = datetime.datetime(1970,1,1).replace(tzinfo=pytz.UTC)
LOCAL_EPOCH = datetime.datetime(1970,1,1).replace(tzinfo=LOCAL_TIMEZONE)

def UTCOffset():
	return int(timedelta_total_seconds((datetime.datetime.now() - datetime.datetime.utcnow()))/60)

def nowLocalTimestamp():
	now = datetime.datetime.now()
	return int(time.mktime(now.timetuple())) - TIMEZONE_OFFSET

def timezoneOffsetMinutes():
	return int(round(TIMEZONE_OFFSET/60.0))

def startOfDayLocalTimestamp():
	sod = startOfDayLocal()
	return int(time.mktime(sod.timetuple())) - TIMEZONE_OFFSET

def startOfDayLocal():
	now = datetime.datetime.utcnow()
	sod = datetime.datetime(year=now.year,month=now.month,day=now.day)
	return sod

def timeInDayLocalSeconds():
	return int(nowLocalTimestamp() - startOfDayLocalTimestamp()) + TIMEZONE_OFFSET

def timeInDayLocalMinutes():
	now = datetime.datetime.now().replace(microsecond=0, second=0)
	return int(time.mktime(now.timetuple()))

def nowLocal():
	return datetime.datetime.now(tz=LOCAL_TIMEZONE)

def nowLocalSecs():
	now = calendar.timegm(time.gmtime())
	return int(now)

def nowUTC():
	return datetime.datetime.now()

def matchMinusOne(m):
	return str(int(m.group(0)) -1)

def fixWrongYear(year_string):
	import re
	return re.sub('\d\d\d\d',matchMinusOne,year_string,1)

def convertStringToUTCTimestamp(date_str):
	"""Takes an XMLTV datetime string and converts it into epoch seconds (UTC)."""

	# returns a UTC datetime object based on offset of programs.
	if date_str.endswith('-0500'):  # conditional XMLTV vs JSONTV
		date_str_notz = date_str[:-6]  # strips -0500 offset.
	else:  # for JSONTV, just copy the variable.
		date_str_notz = date_str
	# two diff formats here. lets use a try/except.
	try:  # new JSONTV: '2014-10-24 00:00:00'
		dtobj = datetime.datetime.strptime(date_str_notz, '%Y-%m-%d %H:%M:%S')
	except:
		try:  # XMLTV.
			dtobj = datetime.datetime.strptime(date_str_notz, '%Y%m%d%H%M%S')  # create dtobj w/str.
		except Exception as e:
			print("ERROR: I could not parse date_str :: {0} :: {1}".format(date_str, e))
	#Time changed to UTC
	dt = pytz.timezone("UTC").localize(dtobj) # localize since times expressed in eastern.
	utc_dt = pytz.utc.normalize(dt.astimezone(pytz.utc))  # convert to UTC, object is aware.
	# return "epoch seconds" from UTC.
	secs = timedelta_total_seconds(utc_dt - UTC_EPOCH)
	return int(secs)

def eastern2utc(intake):
	utc = pytz.utc
	eastern = pytz.timezone('US/Eastern')
	fmt = '%Y-%m-%d %H:%M:%S'
	date = datetime.datetime(*(time.strptime(intake, fmt)[0:6]))
	date_eastern = eastern.localize(date, is_dst=False)
	date_utc = date_eastern.astimezone(utc)
	d2 = date_utc.strftime(fmt)
	d2 = time.strptime(d2, '%Y-%m-%d %H:%M:%S')

	d3 = calendar.timegm(d2)
	# start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(d3)))
	return d3

def string2secs(intake):
	utc = pytz.utc
	fmt = '%Y-%m-%d %H:%M:%S'
	date = datetime.strptime(intake, "%Y-%m-%d %H:%M:%S")
	date_utc = utc.localize(date, is_dst=None)
	# date_utc = date.astimezone(utc)
	d2 = date_utc.strftime(fmt)
	d2 = time.strptime(d2, '%Y-%m-%d %H:%M:%S')
	d3 = calendar.timegm(d2)
	return d3

def secs2string(intake):
	intake = abs(intake)
	start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(float(intake)))
	return start_time

def secs2stringLocal(intake):
	intake = abs(intake)
	start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(intake)))
	return start_time

def secs2stringLocal_time(intake):
	intake = abs(intake)
	hours = time.strftime('%H', time.localtime(float(intake)))
	mins = time.strftime(':%M', time.localtime(float(intake)))
	if int(hours) > 21:
		start_time = str(int(hours)-12) + str(mins) + 'pm'
	elif int(hours) > 12:
		start_time = '0' + str(int(hours)-12) + str(mins) + 'pm'
	else:
		start_time = str(hours) + str(mins) + 'am'
	return start_time

def secs2stringLocal_dur(intake):
	intake = abs(intake)
	start_time = time.strftime('%H:%M', time.gmtime(float(intake)))
	return start_time

def durationString(start, end):
	"""Returns a relative time based on stop-start (duration) time."""

	seconds = end-start  # first math.
	seconds = (round(seconds))
	minutes, seconds = divmod(seconds, 60)
	hours, minutes = divmod(minutes, 60)
	days, hours = divmod(hours, 24)
	minutes = (minutes)
	hours = (hours)
	days = (days)
	# start to prepare output.
	duration = []
	if days > 0:
		duration.append('%dd' % days)
	if hours > 0:
		duration.append('%dh' % hours)
	if minutes > 0:
		duration.append('%dm' % minutes)
	if seconds > 0:
		duration.append('%ds' % seconds)
	# return w/o any spaces. 1m, 2h30m, etc.
	return ''.join(duration)

