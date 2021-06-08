# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals
from future import standard_library
from future.builtins import *
import requests
import os
import re, copy
import time, datetime, calendar
from . import timeutils
import xbmc, xbmcgui
import json, zipfile, shutil, gzip, threading
import urllib
import html.entities as htmlentitydefs
import sys
sys.path.append("..")
from .. import util, settings
from requests import get

try:
	import cPickle as pickle
except:
	import pickle


def cleanup():
	cleaning = [os.path.join(util.PROFILE, 'serviceOperating'),
	            os.path.join(util.PROFILE, fetch['alt']['json'] + '.downloading'),
	            os.path.join(util.PROFILE, fetch['full']['json'] + '.downloading'),
	            os.path.join(util.PROFILE, fetch['sports']['json'] + '.downloading'),
	            os.path.join(util.PROFILE, fetch['alt']['json'] + '.processing'),
	            os.path.join(util.PROFILE, fetch['full']['json'] + '.processing'),
	            os.path.join(util.PROFILE, fetch['sports']['json'] + '.processing')]

	for flag in cleaning:
		if os.path.exists(flag):
			os.remove(flag)


def purge():
	for a,b,files in os.walk(util.PROFILE):
		for file in files:
			os.remove(os.path.join(util.PROFILE,file))


def fix_text(text):
	try:
		return htmlentitydecode(str.encode(text))
		return htmlentitydecode(text.encode('ISO 8859-1'))
	except:
		# util.DEBUG_LOG('Encoding fix failed for: {0} - assuming utf-8'.format(repr(text)))
		return htmlentitydecode(text)


def htmlentitydecode(s):
	if not '&' in s:
		return s
	return re.sub('&(%s);' % '|'.join(str(htmlentitydefs.name2codepoint)),
	              lambda m: (htmlentitydefs.name2codepoint[m.group(1)]), s)

	re.sub()


# Kodi version check for SSL
kodi_version = int(xbmc.getInfoLabel('System.BuildVersion').split('.', 1)[0])
BASE_JSONTVURL = 'https://fast-guide.smoothstreams.tv/'

fetch = {'sports': {'zip': 'feed-new-latest.zip', 'file': 'feed-new.json', 'json': 'sportsepg.json', 'type': 'zip'},
         'full': {'zip': 'feed-new-full-latest.zip', 'file': 'feed-new-full.json', 'json': 'fullepg.json',
                  'type': 'zip'},
         'alt': {'zip': 'feedall1.json.gz', 'file': 'feedall1.json', 'json': 'altepg.json', 'type': 'gzip'}
         }

testfile = ''
JSONFILE_ERROR = os.path.join(util.PROFILE, "SmoothStreams.json.error")
EPGTYPE = ''

LOGOBASE = '{0}'
NEW_LOGOBASE = 'https://fast-guide.smoothstreams.tv/assets/images/channels/{0}-kodi.png'

SPORTS_TABLE = { 'soccer':          {'name':'World Football',   'color':'1E9C2A'},
                 'nfl':             {'name':'American Football','color':'E85F10'},
                 'football':        {'name':'American Football','color':'E85F10'},
                 'american football':{'name':'American Football','color':'E85F10'},
                 'world football':  {'name':'World Football',   'color':'1E9C2A'},
                 'cfb':             {'name':'NCAAF',            'color':'E85F10'},
                 'ncaaf':           {'name':'NCAAF',            'color':'E85F10'},
                 'mlb':             {'name':'Baseball',         'color':'D49F24'},
                 'baseball':        {'name':'Baseball',         'color':'D49F24'},
                 'nba':             {'name':'NBA',              'color':'FC4F3D'},
                 'basketball':      {'name':'NBA',              'color':'FC4F3D'},
                 'boxing':          {'name':'Boxing & MMA',     'color':'808080'}, #white
                 'mma':             {'name':'Boxing & MMA',     'color':'808080'}, #white
                 'boxing + mma':    {'name':'Boxing & MMA',     'color':'808080'}, #white
                 'tennis':          {'name':'Tennis',           'color':'00A658'},
                 'f1':              {'name':'Motor Sports',     'color':'D10404'},
                 'motor sports':    {'name':'Motor Sports',     'color':'D10404'},
                 'racing':          {'name':'Motor Sports',     'color':'D10404'},
                 'wrestling':       {'name':'Wrestling',        'color':'9C793D'},
                 'rugby':           {'name':'Rugby',            'color':'A5AB24'},
                 'other':           {'name':'Other Sports',     'color':'808080'}, #white
                 'other sports':    {'name':'Other Sports',     'color':'808080'}, #white
                 'golf':            {'name':'Golf',             'color':'1EBD06'},
                 'cricket':         {'name':'Cricket',          'color':'3DB800'},
                 'tv':              {'name':'TV Shows',         'color':'808080'},
                 'general tv':      {'name':'TV Shows',         'color':'808080'},
                 'tv shows':        {'name':'TV Shows',         'color':'808080'},
                 'nascar':          {'name':'Nascar',           'color':'D10404'},
                 'nhl':             {'name':'Ice Hockey',       'color':'1373D4'},
                 'hockey':          {'name':'Ice Hockey',       'color':'1373D4'},
                 'ice hockey':      {'name':'Ice Hockey',       'color':'1373D4'},
                 'cbb':             {'name':'NCAAB',            'color':'B0372A'},
                 'ncaab':           {'name':'NCAAB',            'color':'B0372A'},
                 'olympics':        {'name':'Olympics',         'color':'808080'} }  #white

SUBCATS = { '- NCAAF':     'American Football',
            '- NFL':       'American Football',
            '- NBA':       'Basketball',
            '- NCAAB':     'Basketball',
            '- Formula 1': 'Motor Sports',
            '- Nascar':    'Motor Sports',
            '- General TV':'TV Shows'
}

CATSUBS = { 'American Football':('- NCAAF','- NFL'),
            'Basketball':('- NBA','- NCAAB'),
            'Motor Sports':('- Formula 1','- Nascar'),
            'TV Shows':('- General TV'),

}


def dl(url, file_name):
	# open in binary mode
	with open(file_name, "wb") as file:
		# get request
		response = get(url)
		# write to file
		file.write(response.content)
#==============================================================================
# ==============================================================================
# SSChannel
# ==============================================================================
class SSChannel(dict):
	_ssType = 'CHANNEL'

	def init(self, displayname, logo, old_logo, ID):
		self['ID'] = ID
		self['display-name'] = displayname
		self['logo'] = logo
		self['old_logo'] = old_logo
		return self

	def currentProgram(self):
		for p in self.get('programs', []):
			if p.isAiring(): return p
		return None

	@property
	def title(self):
		return self['display-name']

	@property
	def channelNumber(self):
		return int(self['ID'])


# ==============================================================================
# SSProgram
# ==============================================================================
class SSProgram(object):
	_ssType = 'PROGRAM'

	# ==============================================================================
	# EPGData
	# ==============================================================================
	class EPGData(object):
		def __init__(self, program):
			self.program = program

			self.color = SPORTS_TABLE.get(program.categoryName.lower(), {}).get('color', '808080')
			self.colorGIF = util.makeColorGif(self.color,
			                                  os.path.join(util.COLOR_GIF_PATH, '{0}.gif'.format(self.color)))
			self.duration = (program.duration) / 60
			self.category = ''
			self.icon = ''
			self.quality = ''

		def update(self):
			if self.program.quality:
				if '1080' in self.program.quality:
					self.quality = '1080.png'
			self.versions = '[CR]'.join(self.program.versions)

			localTZ = timeutils.LOCAL_TIMEZONE
			nowDT = timeutils.nowUTC()

			self.start = (self.program.start - self.program.startOfDay) / 60
			self.stop = self.start + self.duration

			sDT = datetime.datetime.fromtimestamp(self.program.start, tz=localTZ)
			eDT = datetime.datetime.fromtimestamp(self.program.stop, tz=localTZ)
			if sDT.day == nowDT.day:
				startDisp = datetime.datetime.strftime(sDT, util.TIME_DISPLAY)
			else:
				startDisp = datetime.datetime.strftime(sDT, '%a {0}'.format(util.TIME_DISPLAY))
			if eDT.day == nowDT.day:
				endDisp = datetime.datetime.strftime(eDT, util.TIME_DISPLAY)
			else:
				endDisp = datetime.datetime.strftime(eDT, '%a {0}'.format(util.TIME_DISPLAY))
			self.startDisp = startDisp

			self.timeDisplay = '{0} - {1}  ({2})'.format(startDisp, endDisp, self.program.displayDuration)

	def __init__(self, pid, data, cat_name, start_of_day, categories, channel_number):
		# xxx  bug on OSX and apple TV
		try:
			int(data['time'])
			self.start = int(data['time'])
		except:
			self.start = timeutils.eastern2utc(data['time'])

		try:
			int(data['time']) + int(data['runtime']) * 60

			self.stop = int(data['time']) + int(data['runtime']) * 60
			source = 'sstv'

		except:
			self.stop = timeutils.eastern2utc(data['end_time'])
			source = 'alt'

		self.channel = int(data['channel'])
		self.channel_number = channel_number
		self.title = fix_text(data['name'])
		self.network = data.get('network', '')
		self.language = data.get('language', '')[:2].upper()
		self.description = fix_text(data.get('description', ''))
		self.channelName = data.get('channelName', '')
		self.channelParent = None
		self.eventID = None
		self.parrentID = None
		self.categoryName = cat_name
		self.catgid = None
		self.fake = data.get('fake', '')

		version = data.get('version')
		self.versions = version and version.split(' ; ') or []

		self.pid = str(pid)
		self.subcategory = None

		if 'category' in data:  # stopgap for category.

			cat = str(data['category']) or 'None'

			if source == 'sstv' and categories[cat]['name'] in SUBCATS:
				self.subcategory = categories[cat]['name']
				cat = SUBCATS[categories[cat]['name']]
			elif source == 'alt':
				for i in SUBCATS:
					if cat in i:
						self.subcategory = i
						cat = SUBCATS[i]
						break


				if data['name'] == 'NBA: Philadelphia 76ers at Detroit Pistons':
					util.LOG(self.subcategory)
					util.LOG(cat)

			self.category = cat.replace('&amp;', '&')
		else:
			self.category = 'None'

		self.quality = data.get('quality') or None
		self.setDuration()

		self.epg = SSProgram.EPGData(self)

		self.update(start_of_day)

	def localStart(self):
		return self.start

	def setDuration(self):
		self.duration = self.stop - self.start

		if self.duration > 31536000:  # Fix for stop year being wrong. May happen as new years approaches
			fixed = timeutils.fixWrongYear(self.stop)
			self.stop = timeutils.string2secs(fixed)
			self.duration = self.stop - self.start
			util.DEBUG_LOG(
				'Bad year for "{0}" ({1}) stop time: {2} fixed: {3}'.format(self.title, self.channel, self.stop, fixed))

		self.displayDuration = timeutils.durationString(self.start, self.stop)

	def update(self, start_of_day):
		self.startOfDay = start_of_day
		self.epg.update()

	def isAiring(self):
		timeInDay = timeutils.timeInDayLocalSeconds() / 60
		return self.epg.start <= timeInDay and self.epg.stop >= timeInDay

	def minutesLeft(self):
		if not self.isAiring(): return 0
		timeInDay = timeutils.timeInDayLocalSeconds() / 60
		return self.epg.stop - timeInDay

	@property
	def channelNumber(self):
		return int(self.channel_number)


# ==============================================================================
# Schedule
# ==============================================================================
class Download():
	def __init__(self):
		self.sscachejson(age=10800)



	@classmethod
	def sscachejson(cls, force=False, age=14400):
		# todo rewrite, a download method that dumps both sports and full
		global testfile

		try: settings.EPGTYPE
		except: settings.EPGTYPE = util.getSetting('guide_source', 'sports').lower()
		testfile = os.path.join(util.PROFILE, fetch[settings.EPGTYPE]['json'])
		util.LOG("CacheJSON: Running...")
		# util.LOG(testfile)
		if (force or not os.path.isfile(testfile) or (os.path.getsize(testfile) < 1) or (
				time.time() - os.stat(testfile).st_mtime > age)):  # under 1 byte or over age old (default 4 hours).
			if force:
				util.LOG("CacheJSON: Refresh forced. Fetching...")
			else:
				util.LOG("CacheJSON: File does not exist, is too small or old. Fetching...")

			try:
				downloadAll = True
				time1 = time.time()
				if downloadAll:
					cls.downloadGzip(fetch['alt'])
					cls.downloadZip(fetch['sports'])
					cls.downloadZip(fetch['full'])
				else:
					if settings.EPGTYPE == 'alt':
						cls.downloadGzip(fetch['alt'])
					else:
						cls.downloadZip(fetch[settings.EPGTYPE])

				time2 = time.time()
				util.LOG("look here download, dl: %s" % (time2-time1))
				util.LOG("CacheJSON: Fetched JSON files.")
			except Exception as e:
				util.notify('Schedule Fetching Error', '{0}'.format(e))
				return False
			return True
		else:
			util.LOG("CacheJSON: JSON file is good.")
			return False

	@classmethod
	def downloadGzip(cls, importType):
		try:
			JSONTVURL = os.path.join(BASE_JSONTVURL, 'altepg') + '/' + importType['zip']
			JSONFILE_ZIP = os.path.join(util.PROFILE, importType['zip'])
			JSONFILE = os.path.join(util.PROFILE, importType['json'])
			response = requests.get(JSONTVURL, timeout=2).status_code
			if response != 200:
				JSONTVURL.replace('fast-', '')
				response = requests.get(JSONTVURL, timeout=2).status_code
				if response != 200: JSONTVURL.replace('.gz', '')
			util.DEBUG_LOG("Downloading: %s" % JSONTVURL)
			dl(JSONTVURL, JSONFILE_ZIP)
			try:
				with gzip.open(JSONFILE_ZIP) as f_in:
					with open(JSONFILE, 'w') as f_out:
						shutil.copyfileobj(f_in, f_out)
			except:
				JSONTVURL = os.path.join(BASE_JSONTVURL, 'altepg') + '/' + importType['file']
				dl(JSONTVURL, JSONFILE)
				util.DEBUG_LOG("Downloading: %s" % JSONTVURL)
			return True
		except:
			return False

	@classmethod
	def downloadZip(cls, importType):
		try:
			util.DEBUG_LOG("download zip called")
			JSONTVURL = os.path.join(BASE_JSONTVURL, importType['zip'])
			JSONFILE_ZIP = os.path.join(util.PROFILE, importType['zip'])
			JSONFILE = os.path.join(util.PROFILE, importType['json'])
			response = requests.get(JSONTVURL, timeout=2).status_code
			if response != 200:
				JSONTVURL.replace('fast-', '')
				response = requests.get(JSONTVURL, timeout=2).status_code
				if response != 200:
					JSONTVURL.replace('.zip', '')
					response = requests.get(JSONTVURL, timeout=2).status_code
					if response != 200: JSONTVURL.replace('guide', 'fast-guide')
			util.DEBUG_LOG("Downloading: %s" % JSONTVURL)
			fileName = os.path.join(util.PROFILE, importType['file'])
			dl(JSONTVURL, JSONFILE_ZIP)
			try:
				with zipfile.ZipFile(JSONFILE_ZIP) as f_in:
					f_in.extractall(util.PROFILE)
				shutil.move(fileName, JSONFILE)
			except:
				JSONTVURL = os.path.join(BASE_JSONTVURL, importType['file'])
				dl(JSONTVURL, JSONFILE)
				util.DEBUG_LOG("Downloading: %s" % JSONTVURL)
			return True
		except:
			return False


# ==============================================================================
# Schedule
# ==============================================================================
class Schedule:
	def __init__(self, LIST=False):
		self.seenCategories = []
		self.seenSubCategories = []
		self.tempChannelStore = {}
		Download.sscachejson(False)

	######################
	# INTERNAL FUNCTIONS #
	######################

	def _categories(self, optcategory=None):
		"""Dictionary of valid SmoothStreams categories. Keys are names."""

		# conditional return of dict or check keys..
		if optcategory:  # if we have optcategory
			if optcategory in SPORTS_TABLE:  # return value.
				return SPORTS_TABLE[optcategory]['name']
			else:  # no key found.
				return None
		else:  # no optcategory so return keys.
			return SPORTS_TABLE.keys()

	def _fixchannel(self, chan):
		"""Fix channel string by stripping leading channel number."""

		chan = re.sub('^\d+.*?-.*?(?=\w)', '', chan)  # \d\d- gone.
		return chan

	# def _chanlookup(self, channel):
	#     """Returns the 24/7 channel value (validated) for a given channel."""
	#
	#     chandict = dict((item['id'], self._fixchannel(item['display-name'])) for item in self.readChannels())
	#     return chandict[int(channel)]

	def _getChannel(self, channels, cid):  # TODO: Something faster
		for c in channels:
			if c[u'id'] == cid:
				return c

	def _readALT(self):
		importType = fetch['alt']
		with open(os.path.join(util.PROFILE, importType['json'])) as json_file:
			settings.JSON['alt'] = json.loads(json_file.read())

	def _readSports(self):
		importType = fetch['sports']
		with open(os.path.join(util.PROFILE, importType['json'])) as json_file:
			settings.JSON['sports'] = json.loads(json_file.read())

	def _readFull(self):
		importType = fetch['full']
		with open(os.path.join(util.PROFILE, importType['json'])) as json_file:
			settings.JSON['full'] = json.loads(json_file.read())

	def _readJSON(self):
		util.LOG("_readJson called")
		# if not os.path.exists(testfile):
		#     util.LOG('No schedule file!')
		#     util.LOG(testfile)
		#     return None
		# open file.
		for first in (True, False):
			try:
				time1 = time.time()
				processAll = True
				if processAll:
					self._readALT()
					self._readSports()
					self._readFull()

				else:
					importType = fetch[settings.EPGTYPE]
					with open(os.path.join(util.PROFILE, importType['json'])) as json_file:
						settings.JSON[settings.EPGTYPE] = json.loads(json_file.read())
				time2 = time.time()
				time3 = time.time()
				util.LOG("look here jsonify, json: %s  ujson: %s" % ((time2-time1),(time3-time2)))

			except Exception as e:

				if first:
					util.ERROR('Failed to read json file - re-fetching...')
					Download()
				else:
					util.ERROR('Failed to read json file on second attempt - giving up')
		return None

	def readChannels(self):
		"""Read all channels in the file."""
		self._readJSON()
		if settings.EPGTYPE == 'alt':
			return self.readAltChannels()
		else:
			tree = settings.JSON[settings.EPGTYPE].get('data')
			categories = settings.JSON[settings.EPGTYPE].get('categories')
			# container for output.
			tmp_channels = {}
			channels = []
			# iterate over items.
			for (k, v) in tree.items():
				cid = int(k)
				displayname = fix_text(fix_text(v['name'].strip()))
				logo = util.getIcon(displayname, v.get('number'))
				old_logo = LOGOBASE.format(v['img'])
				tmp_channels[cid] = SSChannel().init(displayname, logo, old_logo, v.get('number'))

			# Sort channel according to its id
			def getKey(item):
				return int(tmp_channels[item]['ID'])

			tmp_tmp_channels = sorted(tmp_channels, key=getKey)

			for cid in tmp_tmp_channels:
				tmp = tmp_channels[cid]
				tmp['id'] = cid
				channels.append(tmp)
			categories['0'] = {u'color': u'FFFFFF', u'image': '', u'name': u'No Category'}

			return channels, categories

	def readAltChannels(self):
		"""Read all channels in the file."""
		tree = settings.JSON['alt']
		if not tree: return None
		# container for output.
		tmp_channels = {}
		channels = []
		# iterate over items.
		for (k, v) in tree.items():
			cid = int(k)
			displayname = v['name']
			logo = util.getIcon(displayname, v.get('channel_id'))
			old_logo = LOGOBASE.format(v['img'])
			tmp_channels[cid] = SSChannel().init(displayname, logo, old_logo, v.get('channel_id'))

		# Sort channel according to its id
		def getKey(item):
			return int(tmp_channels[item]['ID'])

		tmp_tmp_channels = sorted(tmp_channels, key=getKey)

		for cid in tmp_tmp_channels:
			tmp = tmp_channels[cid]
			tmp['id'] = cid
			channels.append(tmp)
		categories = {u'No Category': {u'color': u'FFFFFF', u'image': ''},
		              u"American Football": {u"color": u"FFFFFF", u"image": u"https:\/\/fast-guide.smoothstreams.tv\/assets\/images\/categories\/white\/17.png"},
		              u"- NCAAF": {u"color": u"FFFFFF", u"image": u"https:\/\/fast-guide.smoothstreams.tv\/assets\/images\/categories\/white\/18.png"},
		              u"- NFL": {u"color": u"FFFFFF", u"image": u"https:\/\/fast-guide.smoothstreams.tv\/assets\/images\/categories\/white\/19.png"},
		              u"Baseball": {u"color": u"FFFFFF", u"image": u"https:\/\/fast-guide.smoothstreams.tv\/assets\/images\/categories\/white\/20.png"},
		              u"Basketball": {u"color": u"FFFFFF", u"image": u"https:\/\/fast-guide.smoothstreams.tv\/assets\/images\/categories\/white\/21.png"},
		              u"- NBA": {u"color": u"FFFFFF", u"image": u"https:\/\/fast-guide.smoothstreams.tv\/assets\/images\/categories\/white\/22.png"},
		              u"- NCAAB": {u"color": u"FFFFFF", u"image": u"https:\/\/fast-guide.smoothstreams.tv\/assets\/images\/categories\/white\/23.png"},
		              u"Boxing + MMA": {u"color": u"FFFFFF", u"image": u"https:\/\/fast-guide.smoothstreams.tv\/assets\/images\/categories\/white\/24.png"},
		              u"Cricket": {u"color": u"FFFFFF", u"image": u"https:\/\/fast-guide.smoothstreams.tv\/assets\/images\/categories\/white\/25.png"},
		              u"Golf": {u"color": u"FFFFFF", u"image": u"https:\/\/fast-guide.smoothstreams.tv\/assets\/images\/categories\/white\/26.png"},
		              u"Ice Hockey": {u"color": u"FFFFFF", u"image": u"https:\/\/fast-guide.smoothstreams.tv\/assets\/images\/categories\/white\/27.png"},
		              u"Motor Sports": {u"color": u"FFFFFF", u"image": u"https:\/\/fast-guide.smoothstreams.tv\/assets\/images\/categories\/white\/28.png"},
		              u"- Formula 1": {u"color": u"FFFFFF", u"image": u"https:\/\/fast-guide.smoothstreams.tv\/assets\/images\/categories\/white\/29.png"},
		              u"- Nascar": {u"color": u"FFFFFF", u"image": u"https:\/\/fast-guide.smoothstreams.tv\/assets\/images\/categories\/white\/30.png"},
		              u"Olympics": {u"color": u"FFFFFF", u"image": u"https:\/\/fast-guide.smoothstreams.tv\/assets\/images\/categories\/white\/31.png"},
		              u"Other Sports": {u"color": u"FFFFFF", u"image": u"https:\/\/fast-guide.smoothstreams.tv\/assets\/images\/categories\/white\/32.png"},
		              u"Rugby": {u"color": u"FFFFFF", u"image": u"https:\/\/fast-guide.smoothstreams.tv\/assets\/images\/categories\/white\/33.png"},
		              u"Tennis": {u"color": u"FFFFFF", u"image": u"https:\/\/fast-guide.smoothstreams.tv\/assets\/images\/categories\/white\/34.png"},
		              u"TV Shows": {u"color": u"FFFFFF", u"image": u"https:\/\/fast-guide.smoothstreams.tv\/assets\/images\/categories\/white\/35.png"},
		              u"- General TV": {u"color": u"FFFFFF", u"image": u"https:\/\/fast-guide.smoothstreams.tv\/assets\/images\/categories\/white\/36.png"},
		              u"World Football": {u"color": u"FFFFFF", u"image": u"https:\/\/fast-guide.smoothstreams.tv\/assets\/images\/categories\/white\/37.png"},
		              u"Wrestling": {u"color": u"FFFFFF", u"image": u"https:\/\/fast-guide.smoothstreams.tv\/assets\/images\/categories\/white\/38.png"}}
		return channels, categories


	####################
	# PUBLIC FUNCTIONS #
	####################

	def epg(self, start_of_day):
		util.DEBUG_LOG('schedule EPG called')
		if settings.EPGTYPE == 'alt':
			return self.parseAlt(start_of_day)
		else:
			return self.parseOfficial(start_of_day)

	def parseOfficial(self, start_of_day):
		pid = 1
		t1 = time.time()
		parse = False
		setattr(sys.modules[__name__], 'EPGData', SSProgram.EPGData)  # Ugly AF
		epgPath = os.path.join(util.PROFILE, '{0}.pickle'.format('full' if settings.EPGTYPE == 'full' else 'sports'))
		try:
			if os.path.isfile(epgPath) and (time.time() - os.stat(epgPath).st_mtime < 10800) and (
					os.path.getsize(epgPath) > 1):  # Checking if serialized data isn't too old
				util.DEBUG_LOG('Loading EPG from pickled data...')
				with open(epgPath, 'rb') as pickle_file:
					channels = pickle.load(pickle_file)
				with open(epgPath+'ev', 'rb') as pickle_file:
					eventsChannels = pickle.load(pickle_file)
			else:
				parse = True
		except:
			parse = True
		if parse:
			time1 = time.time()
			channels, categories = self.readChannels()
			if channels == None:
				util.notify('Failed to get schedule', 'Please try again later')
				return []
			eventsChannels = copy.deepcopy(channels)
			intake = settings.JSON[settings.EPGTYPE].get('data')
			for k, v in intake.items():
				if not 'events' in v:
					continue
				if type(v['events']) == list:
					continue

				for key, elem in v['events'].items():
					elem['channel'] = k
					if type(elem['category']) is int:
						elem['category'] = str(elem['category'])

					try:
						cat_name = str(categories[elem['category']]['name'])
					except Exception as e:
						continue

					if cat_name.startswith('-'):
						cat_name = cat_name[2:]

					program = SSProgram(pid, elem, cat_name, start_of_day, categories, v['number'])
					channel = self._getChannel(channels, program.channel)

					ev_channel = self._getChannel(eventsChannels, program.channel)
					program.channelParent = channel
					program.eventID = key
					program.parrentID = elem['parent_id']
					if not 'programs' in channel: channel['programs'] = []
					if not 'programs' in ev_channel: ev_channel['programs'] = []
					try:
						program.catgid = program.category
						program.color = categories[program.category]['color']
						program.category = categories[program.category]['name']
					except Exception as e:
						pass
					if not program.category in self.seenCategories: self.seenCategories.append(program.category)
					if program.subcategory and not program.subcategory in self.seenSubCategories: self.seenSubCategories.append(
						program.subcategory)
					program.channelName = channel['display-name']
					channel['programs'].append(program)
					if not 'source' in elem:
						ev_channel['programs'].append(program)
					pid += 1

			util.DEBUG_LOG('Pickling EPG...')
			with open(epgPath, 'wb') as pickle_file:
				pickle.dump(channels, pickle_file, pickle.HIGHEST_PROTOCOL)
			with open(epgPath+'ev', 'wb') as pickle_file:
				pickle.dump(eventsChannels, pickle_file, pickle.HIGHEST_PROTOCOL)
			time2 = time.time()
			util.LOG("look here parse, official: %s" % (time2 - time1))

		settings.CHANNELS = channels
		settings.EVENTS_CHANNELS = eventsChannels

		return channels

	def parseAlt(self, start_of_day):
		util.LOG('parseAlt called')
		pid = 1
		t1 = time.time()
		parse = False
		epgPath = os.path.join(util.PROFILE, 'alt.pickle')
		setattr(sys.modules[__name__], 'EPGData', SSProgram.EPGData)  # Ugly AF
		try:
			if os.path.isfile(epgPath) and (time.time() - os.stat(epgPath).st_mtime < 10800) and (
					os.path.getsize(epgPath) > 1):  # Checking if serialized data isn't too old
				util.DEBUG_LOG('Loading EPG from pickled data...')
				with open(epgPath, 'rb') as pickle_file:
					channels = pickle.load(pickle_file)
				with open(epgPath + 'ev', 'rb') as pickle_file:
					eventsChannels = pickle.load(pickle_file)
			else:
				parse = True
		except:
			parse = True
		if parse:
			time1 = time.time()
			channels, categories = self.readChannels()
			eventsChannels = copy.deepcopy(channels)
			if channels == None:
				util.notify('Failed to get schedule', 'Please try again later')
				return []
			for k, v in settings.JSON['alt'].items():
				if not 'items' in v: continue

				for elem in v['items']:
					program = SSProgram(pid, elem, elem['category'], start_of_day, categories, elem['channel'])
					channel = self._getChannel(channels, program.channel)
					ev_channel = self._getChannel(eventsChannels, program.channel)

					program.channelParent = channel
					program.eventID = elem['id']
					program.parrentID = elem['parent_id']
					if not 'programs' in channel: channel['programs'] = []
					if not 'programs' in ev_channel: ev_channel['programs'] = []
					try:
						program.catgid = program.category
						program.color = categories[program.category]['color']
						program.category = categories[program.category]['name']
					except Exception as e:
						pass
					if not program.category in self.seenCategories: self.seenCategories.append(program.category)
					if program.subcategory and not program.subcategory in self.seenSubCategories: self.seenSubCategories.append(
						program.subcategory)
					program.channelName = channel['display-name']
					channel['programs'].append(program)
					if elem['source'] == 'ss':
						ev_channel['programs'].append(program)
					pid += 1

			util.DEBUG_LOG('Pickling EPG...')
			with open(epgPath, 'wb') as pickle_file:
				pickle.dump(channels, pickle_file, pickle.HIGHEST_PROTOCOL)
			with open(epgPath+'ev', 'wb') as pickle_file:
				pickle.dump(eventsChannels, pickle_file, pickle.HIGHEST_PROTOCOL)
			time2 = time.time()
			util.LOG("look here parse, alt: %s" % (time2 - time1))


		settings.CHANNELS = channels
		settings.EVENTS_CHANNELS = eventsChannels

		return channels

	def categories(self, subs=False):
		if not subs:  return sorted([s for s in self.seenCategories if not s.startswith('-')])
		# if not subs: return sorted(self.seenCategories)
		cats = []
		for c in sorted(self.seenCategories):
			cats.append(c)
			if c in CATSUBS:
				for s in CATSUBS[c]:
					if s in self.seenSubCategories:
						cats.append('- ' + s)
		return cats
