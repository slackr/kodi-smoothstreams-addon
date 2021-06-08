from __future__ import absolute_import, division, unicode_literals
import os, time, sys, traceback, urllib, gzip, codecs, json, urllib.parse
from datetime import datetime, timedelta
import xbmc, xbmcaddon, xbmcgui, xbmcvfs
from lib import util, settings
from lib.smoothstreams import authutils
from shutil import copyfile
from xml.etree import ElementTree as ET
from urllib.parse import urljoin
from xml.sax.saxutils import escape
import requests

__addon__ = xbmcaddon.Addon()
LOGPATH = xbmcvfs.translatePath('special://logpath')
DATABASEPATH = xbmcvfs.translatePath('special://database')
USERDATAPATH = xbmcvfs.translatePath('special://userdata')
ADDONDATA = xbmcvfs.translatePath(__addon__.getAddonInfo('profile'))
PVRADDONDATA = os.path.join(xbmcvfs.translatePath('special://userdata'), 'addon_data/pvr.iptvsimple')
THUMBPATH = xbmcvfs.translatePath('special://thumbnails')
ADDONLIBPATH = os.path.join(xbmcaddon.Addon(util.ADDON_ID).getAddonInfo('path'), 'lib')
ADDONPATH = xbmcaddon.Addon(util.ADDON_ID).getAddonInfo('path')
KODIPATH = xbmcvfs.translatePath('special://xbmc')
current_offset = 0

jsonExecuteAddon = '{"jsonrpc":"2.0", "method":"Addons.ExecuteAddon", "params": { "wait": false, "addonid": "script.speedtestnet"}, "id":1}'
jsonNotify = '{"jsonrpc":"2.0", "method":"GUI.ShowNotification", "params":{"title":"PVR", "message":"%s","image":""}, "id":1}'
jsonGetPVR = '{"jsonrpc":"2.0", "method":"Settings.GetSettingValue", "params":{"setting":"pvrmanager.enabled"}, "id":1}'
jsonSetPVR = '{"jsonrpc":"2.0", "method":"Settings.SetSettingValue", "params":{"setting":"pvrmanager.enabled", "value":%s},"id":1}'
jsonSetPVR = '{"jsonrpc":"2.0", "method":"Settings.SetSettingValue", "params":{"setting":"pvrmanager.enabled", "value":%s},"id":1}'

def find_between(s, first, last):
	try:
		start = s.index(first) + len(first)
		end = s.index(last, start)
		return s[start:end]
	except ValueError:
		return ""

def dl(url, file_name):
	# open in binary mode
	with open(file_name, "wb") as file:
		# get request
		response = requests.get(url)
		# write to file
		file.write(response.content)

class channelinfo:
	epg = ""
	description = ""
	channum = 0
	channame = ""

class Proxy(object):

	def __init__(self):
		self.addonNeedsRestart = False
		self.chan_map = {}
		try:
			self.pvriptvsimple_addon = xbmcaddon.Addon('pvr.iptvsimple')
			self.chan_map = {}
		except:

			util.LOG("Failed to find pvr.iptvsimple addon")
			util.setSetting("pvrmissing", "true")
			self.pvriptvsimple_addon = None
			pass

	def enableAddons(self):
		json = '{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","params":{"addonid":"pvr.iptvsimple","enabled":true},"id":1}'
		result = xbmc.executeJSONRPC(json)
		json = '{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","params":{"addonid":"inputstream.adaptive","enabled":true},"id":1}'
		result = xbmc.executeJSONRPC(json)

		json = '{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","params":{"addonid":"pvr.demo","enabled":false},"id":1}'
		result = xbmc.executeJSONRPC(json)

		try:
			self.pvriptvsimple_addon = xbmcaddon.Addon('pvr.iptvsimple')
		except:
			util.LOG("Failed to find pvr.iptvsimple addon")
			self.pvriptvsimple_addon = None

		try:
			self.inputadaptive_addon = xbmcaddon.Addon('inputstream.adaptive')

		except Exception:
			util.LOG("Failed to find input adaptive addon")
			self.inputadaptive_addon = None

	def disableAddons(self):
		json = '{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","params":{"addonid":"pvr.iptvsimple","enabled":false},"id":1}'
		result = xbmc.executeJSONRPC(json)
		json = '{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","params":{"addonid":"inputstream.adaptive","enabled":false},"id":1}'
		result = xbmc.executeJSONRPC(json)

		json = '{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","params":{"addonid":"pvr.demo","enabled":false},"id":1}'
		result = xbmc.executeJSONRPC(json)

		try:
			self.pvriptvsimple_addon = xbmcaddon.Addon('pvr.iptvsimple')
		except:
			util.LOG("Failed to find pvr.iptvsimple addon")
			self.pvriptvsimple_addon = None

		try:
			self.inputadaptive_addon = xbmcaddon.Addon('inputstream.adaptive')

		except Exception:
			util.LOG("Failed to find input adaptive addon")
			self.inputadaptive_addon = None

	def restartAddon(self):
		util.LOG("restarting addon")
		xbmcgui.Dialog().ok('SmoothStreams','Restarting, Please wait...')

		json = '{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","params":{"addonid":"pvr.iptvsimple","enabled":"toggle"},"id":1}'
		result = xbmc.executeJSONRPC(json)
		xbmc.sleep(10000)
		json = '{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","params":{"addonid":"pvr.iptvsimple","enabled":true},"id":1}'
		result = xbmc.executeJSONRPC(json)
		xbmcgui.Dialog().ok('SmoothStreams',
		                    'Complete!')

		try:
			self.pvriptvsimple_addon = xbmcaddon.Addon('pvr.iptvsimple')
		except:
			util.LOG("Failed to find pvr.iptvsimple addon")
			self.pvriptvsimple_addon = None
			
	def installAdvSettings(self):
		adv_file = 'advancedsettings.xml'

		adv_file_path = os.path.join(xbmcvfs.translatePath('special://home'),
		                             'addons/' + util.ADDON_ID + '/resources/' + adv_file)
		if os.path.isfile(adv_file_path):
			util.LOG("Advanced Settings file found.  Copying...")
			copyfile(adv_file_path, os.path.join(xbmcvfs.translatePath('special://userdata'), 'advancedsettings.xml'))
			
	def checkAndUpdatePVRIPTVSetting(self, setting, value):
		oldSetting = self.pvriptvsimple_addon.getSetting(setting)
		if oldSetting != value:
			self.pvriptvsimple_addon.setSetting(setting, value)
			self.addonNeedsRestart = True

	def installGenresFile(self):
		try:
			genreFilePath = os.path.join(xbmcvfs.translatePath(PVRADDONDATA), 'genres.xml')
			f = open(genreFilePath, 'w')
			xmldata = """<genres>
		<!---UNDEFINED--->

		<genre type="00">Undefined</genre>

		<!---MOVIE/DRAMA--->

		<genre type="16">Movie/Drama</genre>
		<genre type="16" subtype="01">Detective/Thriller</genre>
		<genre type="16" subtype="02">Adventure/Western/War</genre>
		<genre type="16" subtype="03">Science Fiction/Fantasy/Horror</genre>
		<genre type="16" subtype="04">Comedy</genre>
		<genre type="16" subtype="05">Soap/Melodrama/Folkloric</genre>
		<genre type="16" subtype="06">Romance</genre>
		<genre type="16" subtype="07">Serious/Classical/Religious/Historical Movie/Drama</genre>
		<genre type="16" subtype="08">Adult Movie/Drama</genre>

		<!---NEWS/CURRENT AFFAIRS--->

		<genre type="32">News/Current Affairs</genre>
		<genre type="32" subtype="01">News/Weather Report</genre>
		<genre type="32" subtype="02">News Magazine</genre>
		<genre type="32" subtype="03">Documentary</genre>
		<genre type="32" subtype="04">Discussion/Interview/Debate</genre>

		<!---SHOW--->

		<genre type="48">Show/Game Show</genre>
		<genre type="48" subtype="01">Game Show/Quiz/Contest</genre>
		<genre type="48" subtype="02">Variety Show</genre>
		<genre type="48" subtype="03">Talk Show</genre>

		<!---SPORTS--->

		<genre type="64">Sports</genre>
		<genre type="64" subtype="01">Special Event</genre>
		<genre type="64" subtype="02">Sport Magazine</genre>
		<genre type="96" subtype="03">Football</genre>
		<genre type="144">Tennis/Squash</genre>
		<genre type="64" subtype="05">Team Sports</genre>
		<genre type="64" subtype="06">Athletics</genre>
		<genre type="160">Motor Sport</genre>
		<genre type="64" subtype="08">Water Sport</genre>
		<genre type="64" subtype="09">Winter Sports</genre>
		<genre type="64" subtype="10">Equestrian</genre>
		<genre type="176">Martial Sports</genre>
		<genre type="16">Basketball</genre>
		<genre type="32">Baseball</genre>
		<genre type="48">Soccer</genre>
		<genre type="80">Ice Hockey</genre>
		<genre type="112">Golf</genre>
		<genre type="128">Cricket</genre>


		<!---CHILDREN/YOUTH--->

		<genre type="80">Children's/Youth Programmes</genre>
		<genre type="80" subtype="01">Pre-school Children's Programmes</genre>
		<genre type="80" subtype="02">Entertainment Programmes for 6 to 14</genre>
		<genre type="80" subtype="03">Entertainment Programmes for 16 to 16</genre>
		<genre type="80" subtype="04">Informational/Educational/School Programme</genre>
		<genre type="80" subtype="05">Cartoons/Puppets</genre>

		<!---MUSIC/BALLET/DANCE--->

		<genre type="96">Music/Ballet/Dance</genre>
		<genre type="96" subtype="01">Rock/Pop</genre>
		<genre type="96" subtype="02">Serious/Classical Music</genre>
		<genre type="96" subtype="03">Folk/Traditional Music</genre>
		<genre type="96" subtype="04">Musical/Opera</genre>
		<genre type="96" subtype="05">Ballet</genre>

		<!---ARTS/CULTURE--->

		<genre type="112">Arts/Culture</genre>
		<genre type="112" subtype="01">Performing Arts</genre>
		<genre type="112" subtype="02">Fine Arts</genre>
		<genre type="112" subtype="03">Religion</genre>
		<genre type="112" subtype="04">Popular Culture/Traditional Arts</genre>
		<genre type="112" subtype="05">Literature</genre>
		<genre type="112" subtype="06">Film/Cinema</genre>
		<genre type="112" subtype="07">Experimental Film/Video</genre>
		<genre type="112" subtype="08">Broadcasting/Press</genre>
		<genre type="112" subtype="09">New Media</genre>
		<genre type="112" subtype="10">Arts/Culture Magazines</genre>
		<genre type="112" subtype="11">Fashion</genre>

		<!---SOCIAL/POLITICAL/ECONOMICS--->

		<genre type="128">Social/Political/Economics</genre>
		<genre type="128" subtype="01">Magazines/Reports/Documentary</genre>
		<genre type="128" subtype="02">Economics/Social Advisory</genre>
		<genre type="128" subtype="03">Remarkable People</genre>

		<!---EDUCATIONAL/SCIENCE--->

		<genre type="144">Education/Science/Factual</genre>
		<genre type="144" subtype="01">Nature/Animals/Environment</genre>
		<genre type="144" subtype="02">Technology/Natural Sciences</genre>
		<genre type="144" subtype="03">Medicine/Physiology/Psychology</genre>
		<genre type="144" subtype="04">Foreign Countries/Expeditions</genre>
		<genre type="144" subtype="05">Social/Spiritual Sciences</genre>
		<genre type="144" subtype="06">Further Education</genre>
		<genre type="144" subtype="07">Languages</genre>

		<!---LEISURE/HOBBIES--->

		<genre type="160">Leisure/Hobbies</genre>
		<genre type="160" subtype="01">Tourism/Travel</genre>
		<genre type="160" subtype="02">Handicraft</genre>
		<genre type="160" subtype="03">Motoring</genre>
		<genre type="160" subtype="04">Fitness &amp; Health</genre>
		<genre type="160" subtype="05">Cooking</genre>
		<genre type="160" subtype="06">Advertisement/Shopping</genre>
		<genre type="160" subtype="07">Gardening</genre>

		<!---SPECIAL--->

		<genre type="176">Special Characteristics</genre>
		<genre type="176" subtype="01">Original Language</genre>
		<genre type="176" subtype="02">Black &amp; White</genre>
		<genre type="176" subtype="03">Unpublished</genre>
		<genre type="176" subtype="04">Live Broadcast</genre>


		</genres>"""
			f.write(xmldata)
			f.close()
			util.LOG("Copying...Genres file")


		except Exception as e:
			util.LOG("Error copying genre file \n{0}\n{1}".format(e, traceback.format_exc()))
			pass
	
	def dl_epg(self, source=1):
		if self.chan_map == {}: self.build_playlist()
		# download epg xml
		name = None
		if util.getSetting('guide_source', 'sports').lower() == 'sports':
			name = 'sports.xml'
		else:
			name = 'epg.xml'
		if os.path.isfile(os.path.join(util.PROFILE, 'epg.xml')):

			copyfile(os.path.join(util.PROFILE, name), os.path.join(PVRADDONDATA, 'xmltv.xml.cache'))
			util.LOG("Written xmltv")
			existing = os.path.join(util.PROFILE, 'epg.xml')
			cur_utc_hr = datetime.utcnow().replace(microsecond=0, second=0, minute=0).hour
			target_utc_hr = (cur_utc_hr // 3) * 3
			target_utc_datetime = datetime.utcnow().replace(microsecond=0, second=0, minute=0, hour=target_utc_hr)
			util.DEBUG_LOG("utc time is: %s,    utc target time is: %s,    file time is: %s" % (
				datetime.utcnow(), target_utc_datetime, datetime.utcfromtimestamp(os.stat(existing).st_mtime)))
			if os.path.isfile(existing) and os.stat(existing).st_mtime > int(
					(time.mktime(target_utc_datetime.timetuple()) + target_utc_datetime.microsecond / 1000000.0)):
				util.DEBUG_LOG("Skipping download of epg")
				return
		to_process = []
		if source == 1:
			util.LOG("Downloading epg")
			dl("https://fast-guide.smoothstreams.tv/altepg/xmltv5.xml.gz",
			                   os.path.join(util.PROFILE, 'rawepg.xml.gz'))
			unzipped = os.path.join(util.PROFILE, 'rawepg.xml.gz')
			to_process.append([unzipped, "epg.xml", 'fog'])
			dl("https://fast-guide.smoothstreams.tv/feed.xml",
			                   os.path.join(util.PROFILE, 'rawsports.xml'))
			unzippedsports = os.path.join(util.PROFILE, 'rawsports.xml')
			to_process.append([unzippedsports, "sports.xml", 'sstv'])
		else:
			util.LOG("Downloading sstv epg")
			dl("https://fast-guide.smoothstreams.tv/feed.xml",
			                   os.path.join(util.PROFILE, 'rawepg.xml'))
			unzipped = os.path.join(util.PROFILE, 'rawepg.xml')
			to_process.append([unzipped, "epg.xml", 'sstv'])
			to_process.append([unzipped, "sports.xml", 'sstv'])
		for process in to_process:
			# try to categorise the sports events
			if process[0].endswith('.gz'):
				opened = gzip.open(process[0])
			else:
				opened = codecs.open(process[0], encoding="UTF-8")
			source = ET.parse(opened)
			root = source.getroot()
			changelist = {}

			with open(os.path.join(util.PROFILE, 'prep.xml'), 'w') as f:
				f.write('<?xml version="1.0" encoding="UTF-8"?>'.rstrip('\r\n'))
				f.write('''<tv><channel id="static_refresh"><display-name lang="en">Static Refresh</display-name><icon src="http://speed.guide.smoothstreams.tv/assets/images/channels/150.png" /></channel><programme channel="static_refresh" start="20170118213000 +0000" stop="20201118233000 +0000"><title lang="us">Press to refresh rtmp channels</title><desc lang="en">Select this channel in order to refresh the RTMP playlist. Only use from the channels list and NOT the guide page. Required every 4hrs.</desc><category lang="us">Other</category><episode-num system="">1</episode-num></programme></tv>''')
			desttree = ET.parse(os.path.join(util.PROFILE, 'prep.xml'))
			desttreeroot = desttree.getroot()


			for channel in source.findall('channel'):
				if process[2] == 'fog':
					b = channel.find('display-name')
					newname = [self.chan_map[x].channum for x in range(len(self.chan_map) + 1) if
					           x != 0 and self.chan_map[x].epg == channel.attrib['id'] and self.chan_map[x].channame == b.text]
					if len(newname) > 1:
						util.DEBUG_LOG("EPG rename conflict %s" % ",".join(newname))
					# It's a list regardless of length so first item is always wanted.
					newname = newname[0]
					changelist[channel.attrib['id']] = newname
					channel.attrib['id'] = newname
				b = channel.find('display-name')
				try: b.text = escape((b.text))
				except: b.text = ''
				desttreeroot.append(channel)

			for programme in source.findall('programme'):
				if process[2] == 'fog':
					try:
						programme.attrib['channel'] = changelist[programme.attrib['channel']]
					except:
						util.LOG("A programme was skipped as it couldn't be assigned to a channel, refer log.")
						util.DEBUG_LOG("%s %s" %(programme.find('title').text, programme.attrib))


				desc = programme.find('desc')
				if desc is None:
					ET.SubElement(programme, 'desc')
					desc = programme.find('desc')
					desc.text = ""
				elif desc.text == 'None':
					desc.text = ""
				else:
					try: desc.text = escape((desc.text))
					except: desc.text = ""


				sub = programme.find('sub-title')
				if sub is None:
					ET.SubElement(programme, 'sub-title')
					sub = programme.find('sub-title')
					sub.text = ""
				else:
					try: sub.text = escape((sub.text))
					except: sub.text = ""


				title = programme.find('title')
				try: title.text = escape((title.text))
				except: title.text = ''

				cat = programme.find('category')
				if cat is None:
					ET.SubElement(programme, 'category')
					cat = programme.find('category')

				if process[2] == 'sstv':
					cat.text = 'Sports'
				ep_num = programme.find('episode-num')
				# emby
				# sports|basketball|baseball|football|Rugby|Soccer|Cricket|Tennis/Squash|Motor Sport|Golf|Martial Sports|Ice Hockey|Alpine Sports|Darts
				if cat.text == "Sports":
					if any(sport in title.text.lower() for sport in
					       ['nba', 'ncaam', 'nba', 'basquetebol', 'wnba', 'g-league']):
						cat.text = "Basketball"
					elif any(sport in title.text.lower() for sport in
					         ['nfl', 'football', 'american football', 'ncaaf', 'cfb']):
						cat.text = "Football"
					elif any(sport in title.text.lower() for sport in
					         ['epl', 'efl', 'fa cup', 'spl', 'taca de portugal', 'w-league', 'soccer', 'ucl',
					          'coupe de la ligue', 'league cup', 'mls', 'uefa', 'fifa', 'fc', 'la liga', 'serie a',
					          'wcq', 'khl:', 'shl:', '1.bl:', 'euroleague', 'knvb', 'superliga turca',
					          'liga holandesa']):
						cat.text = "Soccer"
					elif any(sport in title.text.lower() for sport in
					         ['rugby', 'nrl', 'afl', 'rfu', 'french top 14:', "women's premier 15",
					          'guinness pro14']):
						cat.text = "Rugby"
					elif any(sport in title.text.lower() for sport in ['cricket', 't20', 't20i']):
						cat.text = "Cricket"
					elif any(sport in title.text.lower() for sport in ['tennis', 'squash', 'atp']):
						cat.text = "Tennis/Squash"
					elif any(sport in title.text.lower() for sport in ['f1', 'nascar', 'motogp', 'racing']):
						cat.text = "Motor Sport"
					elif any(sport in title.text.lower() for sport in ['golf', 'pga']):
						cat.text = "Golf"
					elif any(sport in title.text.lower() for sport in ['boxing', 'mma', 'ufc', 'wrestling', 'wwe']):
						cat.text = "Martial Sports"
					elif any(sport in title.text.lower() for sport in ['hockey', 'nhl', 'ice hockey', 'iihf']):
						cat.text = "Ice Hockey"
					elif any(sport in title.text.lower() for sport in
					         ['baseball', 'mlb', 'beisbol', 'minor league', 'ncaab']):
						cat.text = "Baseball"
					elif any(sport in title.text.lower() for sport in ['news']):
						cat.text = "News"
					elif any(sport in title.text.lower() for sport in ['alpine', 'skiing', 'snow']):
						cat.text = "Alpine Sports"
					elif any(sport in title.text.lower() for sport in ['darts']):
						cat.text = "Darts"
				desttreeroot.append(programme)
			desttree.write(os.path.join(util.PROFILE, process[1]))
			util.DEBUG_LOG("writing to %s" % process[1])
			# add xml header to file for Kodi support
			with open(os.path.join(util.PROFILE, process[1]), 'r+') as f:
				content = f.read()
				# staticinfo = '''<channel id="static_refresh"><display-name lang="en">Static Refresh</display-name><icon src="http://speed.guide.smoothstreams.tv/assets/images/channels/150.png" /></channel><programme channel="static_refresh" start="20170118213000 +0000" stop="20201118233000 +0000"><title lang="us">Press to refresh Kodi PVR</title><desc lang="en">Select this channel in order to refresh the Kodi PVR data. Only use from the channels list and NOT the guide page.</desc><category lang="us">Other</category><episode-num system="">1</episode-num></programme></tv>'''
				# content = content[:-5] + staticinfo
				f.seek(0, 0)
				f.write('<?xml version="1.0" encoding="UTF-8"?>'.rstrip('\r\n') + content)
			if name == process[1]:
				desttree.write(os.path.join(PVRADDONDATA, 'xmltv.xml.cache'))
				with open(os.path.join(PVRADDONDATA, 'xmltv.xml.cache'), 'r+') as f:
					content = f.read()
					# staticinfo = '''<channel id="static_refresh"><display-name lang="en">Static Refresh</display-name><icon src="http://speed.guide.smoothstreams.tv/assets/images/channels/150.png" /></channel><programme channel="static_refresh" start="20170118213000 +0000" stop="20201118233000 +0000"><title lang="us">Press to refresh Kodi PVR</title><desc lang="en">Select this channel in order to refresh the Kodi PVR data. Only use from the channels list and NOT the guide page.</desc><category lang="us">Other</category><episode-num system="">1</episode-num></programme></tv>'''
					# content = content[:-5] + staticinfo
					f.seek(0, 0)
					f.write('<?xml version="1.0" encoding="UTF-8"?>'.rstrip('\r\n') + content)
	
	def updatePVRSettings(self):
		util.LOG('updating pvr settings')
		advFile = os.path.join(xbmcvfs.translatePath('special://userdata'), 'advancedsettings.xml')
		genreFile = os.path.join(xbmcvfs.translatePath(PVRADDONDATA), 'genres.xml')
	
		if os.path.exists(advFile) == False:
			self.installAdvSettings()
	
		if self.pvriptvsimple_addon != None:
	

			m3uPath = 'http://127.0.0.1:9696/playlist.m3u8'
	

			updater_path = os.path.join(xbmcvfs.translatePath('special://userdata'), 'addon_data',util.ADDON_ID, 'Cache','')
	
			offset = str(current_offset)
			if current_offset == '-1000':
				# TODO: Figure out needs for offsets on Krypton
				offset = 0
			# if mc_timezone_enable == True:
			# 	offset = mc_timezone
			if time.localtime().tm_isdst == 1:
				dst = '1'
			else:
				dst = '0'
			timeNow = int(time.time())
			# categorySetupLastOpen = int(util.getSetting('categorySetupLastOpen'))
			# categorySetupLastSet = int(util.getSetting('categorySetupLastSet'))
	
			self.checkAndUpdatePVRIPTVSetting("epgCache", "true")
			self.checkAndUpdatePVRIPTVSetting("epgPathType", "0")
			self.checkAndUpdatePVRIPTVSetting("epgPath", os.path.join(updater_path, 'epg.xml'))
			self.checkAndUpdatePVRIPTVSetting("m3uPathType", "1")
			self.checkAndUpdatePVRIPTVSetting('epgTimeShift', str(dst))
			self.checkAndUpdatePVRIPTVSetting('epgTSOverride', 'true')
			self.checkAndUpdatePVRIPTVSetting('logoFromEpg', '2')
			self.checkAndUpdatePVRIPTVSetting("m3uPath", '')
			self.checkAndUpdatePVRIPTVSetting("m3uUrl", m3uPath)
	
			self.checkAndUpdatePVRIPTVSetting("m3uCache", 'true')
	
			if self.addonNeedsRestart:
				self.dl_epg()
				xbmc.executeJSONRPC(jsonNotify % "Configuring PVR & Guide")
				# xbmc.sleep(10000)
				# self.dl_epg()
	
				# self.restartAddon()
				# xbmc.sleep(5000)
				# PVR = json.loads(xbmc.executeJSONRPC(jsonGetPVR))['result']['value']
				xbmc.executeJSONRPC(jsonNotify % "Live TV Enabled, Restart Kodi")
				xbmc.executeJSONRPC(jsonSetPVR % "false")
				xbmc.executebuiltin('PVR.StartManager')

				xbmc.sleep(1000)






				# xbmc.sleep(500)
				xbmc.executeJSONRPC(jsonSetPVR % "true")

				# xbmc.executebuiltin('XBMC.StartPVRManager')
				util.LOG("restarting pvr complete")
	
				if os.path.exists(genreFile) == False:
					self.installGenresFile()
	
				# if xbmcgui.Dialog().yesno("SmoothStreams",
				#                           'In Order To Complete The Installation We Need To Restart The Application',
				#                           'Would You Like To Restart Now?'):
				# 	xbmc.executebuiltin("Quit")
				# 	sys.exit()
	

	
	
		else:
			if util.getSetting('warning_msg') != True:
				self.kodi_version = xbmc.getInfoLabel('System.BuildVersion').split()[0]
				self.kodi_version = self.kodi_version.split('.')[0]
				if int(self.kodi_version) >= 18:
					xbmcgui.Dialog().ok("SmoothStreams",
					                    'Looks like you are missing PVR IPTV Simple Client.',
					                    'Please install this from the official Kodi Repo. The PVR functionality will not work until this is done',
					                    'This add-on was removed from the base Kodi image in v18.')
				else:
					xbmcgui.Dialog().ok("SmoothStreams", 'Looks like you are missing some important functions inside Kodi.',
					                    'This can happen when you are using a preinstalled version of Kodi. The PVR functionality will not work until this is done',
					                    'Install Kodi or SPMC from the Play Store or kodi.tv, to fix this')
				util.setSetting('warning_msg', 'true')

	def build_playlist(self):
		try:
			a = settings.TOKEN
		except:
			settings.init()
			authutils.load_token()
			authutils.check_token()
		self.chan_map = {}
		SITE = authutils.services[authutils.serviceIDX()]['site']
		util.DEBUG_LOG("Loading channel list")
		url = 'https://fast-guide.smoothstreams.tv/altepg/channels.json'
		jsonChanList = json.loads(requests.get(url).text)

		for item in jsonChanList:
			retVal = channelinfo()
			# print(item)
			oChannel = jsonChanList[item]
			retVal.channum = oChannel["channum"]
			channel = int(oChannel["channum"])
			retVal.channame = oChannel["channame"].replace(format(channel, "02") + " - ", "").strip()
			if retVal.channame == 'Empty':
				retVal.channame = retVal.channum
			retVal.epg = oChannel["xmltvid"]
			self.chan_map[channel] = {}
			self.chan_map[channel] = retVal

		util.DEBUG_LOG("Built channel map with %d channels" % len(self.chan_map))
		# kodi playlist contains two copies of channels, first is dynmaic HLS and the second is static rtmp
		SERVER_HOST = "http://127.0.0.1:9696"
		# build playlist using the data we have
		new_playlist = "#EXTM3U x-tvg-url='http://127.0.0.1:9696/epg.xml'\n"
		# if STRM == 'hls':
		try:
			FAV = [int(x) for x in util.getSetting("FAV").split(',')]
		except:
			FAV = []
		for pos in range(1, len(self.chan_map) + 1):
			logo = util.getIcon(self.chan_map[pos].channame, self.chan_map[pos].channum)
			# build channel url
			url = "playlist.m3u8?ch={0}"
			if util.getSetting("mpeg") == 'true': url = "mpeg.2ts?ch={0}"
			url = "mpeg.2ts?ch={0}"
			urlformatted = url.format(self.chan_map[pos].channum)
			channel_url = urljoin(SERVER_HOST, urlformatted)
			# build playlist entry
			if util.getSetting("server_type", 1) == 1:
				try:
					new_playlist += '#EXTINF:-1 tvg-id="%s" tvg-name="%s" tvg-logo="%s" channel-id="%s" group-title="HLS",%s\n' % (
						self.chan_map[pos].channum, self.chan_map[pos].channame, logo,
						self.chan_map[pos].channum,
						self.chan_map[pos].channame)
					new_playlist += '%s\n' % channel_url
					if pos in FAV:
						new_playlist += '#EXTINF:-1 tvg-id="%s" tvg-name="%s" tvg-logo="%s" channel-id="%s" group-title="Fav",%s\n' % (
							self.chan_map[pos].channum, self.chan_map[pos].channame, logo,
							self.chan_map[pos].channum,
							self.chan_map[pos].channame)
						new_playlist += '%s\n' % channel_url
				except:
					util.ERROR("Exception while updating kodi playlist: ")
			else:
				try:
					new_playlist += '#EXTINF:-1 tvg-id="%s" tvg-name="%s" tvg-logo="%s" channel-id="%s" group-title="MPEG",%s\n' % (
						self.chan_map[pos].channum, self.chan_map[pos].channame, logo,
						self.chan_map[pos].channum,
						self.chan_map[pos].channame)
					new_playlist += '%s\n' % channel_url
					if pos in FAV:
						new_playlist += '#EXTINF:-1 tvg-id="%s" tvg-name="%s" tvg-logo="%s" channel-id="%s" group-title="Fav",%s\n' % (
							self.chan_map[pos].channum, self.chan_map[pos].channame, logo,
							self.chan_map[pos].channum,
							self.chan_map[pos].channame)
						new_playlist += '%s\n' % channel_url
				except:
					util.ERROR("Exception while updating kodi playlist: ")
			# else:
			# 	# build playlist entry
			# 	hash = authutils.check_token()
			# 	try:
			# 		new_playlist += '#EXTINF:-1 tvg-id="%s" tvg-name="%s" tvg-logo="%s" channel-id="%s" group-title="RTMP",%s\n' % (
			# 			self.chan_map[pos].channum, self.chan_map[pos].channame, logo,
			# 			self.chan_map[pos].channum,
			# 			self.chan_map[pos].channame)
			# 		new_playlist += '%s\n' % authutils.getChanUrl(pos, force_rtmp=True)
			# 		if pos in FAV:
			# 			new_playlist += '#EXTINF:-1 tvg-id="%s" tvg-name="%s" tvg-logo="%s" channel-id="%s" group-title="Fav RTMP",%s\n' % (
			# 				self.chan_map[pos].channum, self.chan_map[pos].channame, logo,
			# 				self.chan_map[pos].channum,
			# 				self.chan_map[pos].channame)
			# 			new_playlist += '%s\n' % authutils.getChanUrl(pos, force_rtmp=True)
			# 	except:
			# 		util.ERROR("Exception while updating kodi playlist: ")

		# new_playlist += '#EXTINF:-1 tvg-id="static_refresh" tvg-name="Manual Refresh IPTV" tvg-logo="%s/empty.png" channel-id="151" group-title="HLS",Manual Refresh IPTV\n' % (
		# 	SERVER_HOST)
		# new_playlist += '#EXTINF:-1 tvg-id="static_refresh" tvg-name="Manual Refresh IPTV" tvg-logo="%s/empty.png" channel-id="151" group-title="RTMP",Manual Refresh IPTV\n' % (
		# 	SERVER_HOST)
		new_playlist += '#EXTINF:-1 tvg-id="static_refresh" tvg-name="Manual Refresh IPTV" tvg-logo="%s/empty.png" channel-id="0" group-title="Manual Refresh IPTV",Manual Refresh IPTV\n' % (
			SERVER_HOST)
		new_playlist += '%s/refresh.m3u8\n' % (SERVER_HOST)
		template = '{0}://{1}.smoothstreams.tv:{2}/{3}/ch{4}q{5}.stream{6}?wmsAuthSign={7}'
		url = "{0}/playlist.m3u8?ch=1&type={1}"
		TEST = True if util.getSetting('TEST', 'false') else False
		if TEST:
			new_playlist += '#EXTINF:-1 tvg-id="1" tvg-name="Static HLS" channel-id="1" group-title="Testing","Static HLS"\n'
			new_playlist += '%s\n' % template.format('https', 'dnaw1', '443', SITE, "01", 1, '/playlist.m3u8',
													 settings.TOKEN['hash'])
			new_playlist += '#EXTINF:-1 tvg-id="1" tvg-name="Static MPEG" channel-id="1" group-title="Testing","Static MPEG"\n'
			new_playlist += '%s\n' % template.format('https', 'dnaw1', '443', SITE, "01", 1, '/mpeg.2ts',
													 settings.TOKEN['hash'])
			new_playlist += '#EXTINF:-1 tvg-id="2" tvg-name="Static RTMP" channel-id="2" group-title="Testing","Static RTMP"\n'
			new_playlist += '%s\n' % template.format('rtmp', 'dnaw1', '3625', SITE, "01", 1, '', settings.TOKEN['hash'])
			new_playlist += '#EXTINF:-1 tvg-id="%s" tvg-name="Redirect" channel-id="%s" group-title="Testing","Redirect"\n' % (
			3, 3)
			new_playlist += '%s\n' % url.format(SERVER_HOST, '1')
			new_playlist += '#EXTINF:-1 tvg-id="%s" tvg-name="File" channel-id="%s" group-title="Testing","File"\n' % (
			4, 4)
			new_playlist += '%s\n' % url.format(SERVER_HOST, '2')
			new_playlist += '#EXTINF:-1 tvg-id="%s" tvg-name="Response" channel-id="%s" group-title="Testing","Response"\n' % (
			5, 5)
			new_playlist += '%s\n' % url.format(SERVER_HOST, '3')
			new_playlist += '#EXTINF:-1 tvg-id="%s" tvg-name="URL" channel-id="%s" group-title="Testing","URL"\n' % (
			6, 6)
			new_playlist += '%s\n' % url.format(SERVER_HOST, '4')
			new_playlist += '#EXTINF:-1 tvg-id="%s" tvg-name="Variable" channel-id="%s" group-title="Testing","Variable"\n' % (
			7, 7)
			new_playlist += '%s\n' % url.format(SERVER_HOST, '5')
		util.LOG("Built Kodi %s playlist" %('RTMP' if util.getSetting("server_type", 1) == 0 else 'HLS' if util.getSetting("server_type", 1) == 1 else 'MPEG'))

		with open(os.path.join(util.PROFILE, 'playlist.m3u8'), 'w+') as f:
			f.write(new_playlist)
		with open(os.path.join(PVRADDONDATA, 'iptv.m3u.cache'), 'w+') as f:
			f.write(new_playlist)
		util.LOG("Written m3u8")
		return new_playlist

	def create_hls_channel_playlist(self, url):
		file = requests.get(url).text
		if not os.path.isfile(os.path.join(util.PROFILE, 'channel.m3u8')):
			f = open(os.path.join(util.PROFILE, 'channel.m3u8'), 'w')
			f.close()
		# Used to support HLS HTTPS requests
		file = file.replace('chunks', 'http' + find_between(url,'http','playlist') + 'chunks')
		with open(os.path.join(util.PROFILE, 'channel.m3u8'), 'r+') as f:
			f.write(file)
		return file