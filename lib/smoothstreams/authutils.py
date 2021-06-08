from __future__ import absolute_import, division, unicode_literals
from lib import util
import xbmc, xbmcgui, os, requests, urllib, urllib.parse
from lib import settings
from datetime import datetime, timedelta
import json, time
from json import load, dump

servers = 	{'Euro Mix': "deu.SmoothStreams.tv",  # European Server Mix
			'Euro NL Mix': "deu-nl.SmoothStreams.tv",  # European NL Mix
			'Euro UK Mix': "deu-uk.SmoothStreams.tv",  # European UK Mix
			'Euro DE Mix': "deu-de.SmoothStreams.tv",  # European DE Mix
			'EU FR1 (DP)': "deu-fr1.SmoothStreams.tv",  # European FR1 (DP)
			'EU UK1 (io)': "deu-uk1.SmoothStreams.tv",  # European UK1 (io)
			'EU UK2 (100TB)': "deu-uk2.SmoothStreams.tv",  # European UK2 (100TB)
			'EU NL1 (i3d)': "deu-nl1.SmoothStreams.tv",  # European NL1 (i3d)
			'NA Mix': "dna.SmoothStreams.tv",  # US/CA Server Mix
			'NA East Mix': "dnae.SmoothStreams.tv",  # US/CA East Server Mix
			'NA West Mix': "dnaw.SmoothStreams.tv",  # US/CA West Server Mix
			'NA East 1 (NJ)': "dnae1.SmoothStreams.tv",  # US/CA East 1 (NJ)
			'NA East 2 (NY)': "dnae2.SmoothStreams.tv",  # US/CA East 2 (VA)
			'NA East 3 (CHI)': "dnae3.SmoothStreams.tv",  # US/CA East 3 (MTL)
			'NA East 4 (ATL)': "dnae4.SmoothStreams.tv",  # US/CA East 4 (TOR)
			'NA East 5 (VA)': "dnae5.SmoothStreams.tv",  # US/CA East 5 (ATL)
			'NA West 1 (PHX)': "dnaw1.SmoothStreams.tv",  # US/CA West 1 (PHX,AZ)
			'NA West 2 (LA)': "dnaw2.SmoothStreams.tv",  # US/CA West 2 (LA,CA)
			'Asia Mix': "dap.SmoothStreams.tv",  # Asia - Mix
			'Asia SG 1 (SL)': "dap1.SmoothStreams.tv",  # Asia - SG 1 (SL)
			'Asia SG 2 (OVH)': "dap2.SmoothStreams.tv",  # Asia - SG 2 (OVH)
			'Asia SG 3 (DO)': "dap3.SmoothStreams.tv"}  # Asia - SG 3 (DO)

# Kodi version check for SSL
kodi_version = int(xbmc.getInfoLabel('System.BuildVersion').split('.', 1)[0])
HASH_LOGIN = 'https://auth.smoothstreams.tv/hash_api.php?site={site}&username={user}&password={password}'
MMA_HASH_LOGIN = 'https://www.MMA-TV.net/loginForm.php?username={user}&password={password}&site={site}'
services = (
	{'name': 'Live247.tv', 'site': "view247", 'rtmp_port': 3625, 'hls_port': 443, 'login': HASH_LOGIN},
	{'name': 'StarStreams', 'site': "viewss", 'rtmp_port': 3665, 'hls_port': 443, 'login': HASH_LOGIN},
	{'name': 'MMA SR+', 'site': "viewmmasr", 'rtmp_port': 3635, 'hls_port': 443, 'login': MMA_HASH_LOGIN},
	{'name': 'StreamTVnow', 'site': "viewstvn", 'rtmp_port': 3615, 'hls_port': 443, 'login': HASH_LOGIN}
)



TOKEN_PATH = os.path.join(util.PROFILE, 'token.json')


def load_token():
	if os.path.exists(TOKEN_PATH):
		with open(TOKEN_PATH, 'r+') as fp:
			settings.TOKEN = load(fp)
			settings.TOKEN['hash'] = str(settings.TOKEN['hash'])
			util.DEBUG_LOG("Loaded token %r, expires at %s" % (settings.TOKEN['hash'], settings.TOKEN['expires']))
	else:
		dump_token()


def dump_token():
	with open(TOKEN_PATH, 'w') as fp:
		dump(settings.TOKEN, fp)
		util.DEBUG_LOG("Dumped token.json")


def check_token(force=False):
	# load and check/renew token
	if not settings.TOKEN['hash'] or not settings.TOKEN['expires']:
		# fetch fresh token
		util.DEBUG_LOG("There was no token loaded, retrieving your first token...")
		get_auth_token()
		dump_token()
	elif force:
		# fetch new token
		util.DEBUG_LOG("Force refresh requested, retrieving new token...")
		get_auth_token()
		dump_token()
	else:
		try:
			# check / renew token
			if datetime.now() > datetime(*(time.strptime(settings.TOKEN['expires'], "%Y-%m-%d %H:%M:%S.%f")[0:6])):
			# if datetime.now() > datetime.strptime(settings.TOKEN['expires'], "%Y-%m-%d %H:%M:%S.%f"):
				# token is expired, renew
				util.DEBUG_LOG("Token has expired, retrieving a new one...")
				get_auth_token()
				dump_token()
		except:
			get_auth_token()
			dump_token()
	return settings.TOKEN['hash']


def serviceIDX():
	idx = util.getSetting("service", 0)
	if idx >= len(services):
		idx = len(services) - 1
	return int(idx)


def get_auth_token():
	site = services[serviceIDX()]['site']
	params = {
		"username": util.getSetting("username"),
		"password": util.getSetting("user_password"),
		"site": site
	}

	if site == 'viewmmasr' or site == 'mmatv':
		baseUrl = 'https://www.mma-tv.net/loginForm.php?'

	else:
		baseUrl = 'https://auth.smoothstreams.tv/hash_api.php?'

	session = requests.Session()
	headers = {'User-Agent': util.USER_AGENT}
	url = baseUrl + urllib.parse.urlencode(params)
	# util.LOG('URL: %s' % url)
	try:
		data = session.post(url, params, headers=headers, timeout=10).json()
	except:
		data = {}
		util.ERROR("There was no response from %s..." % baseUrl)
		util.ERROR("Closing...")
		return
	if 'hash' not in data or 'valid' not in data:
		util.LOG("Data: %s" % data)
		util.ERROR("There was no hash auth token returned from %s..." % baseUrl)
		util.ERROR("Closing...")
		xbmcgui.Dialog().ok('SmoothStreams',
		                    "There was no hash auth token returned from SSTV, check your username and password are correct and that you've selected the correct service (%s)" % site)
		util.openSettings()

		return
	else:
		settings.TOKEN['hash'] = str(data['hash'])
		settings.TOKEN['expires'] = (datetime.now() + timedelta(minutes=data['valid'])).strftime("%Y-%m-%d %H:%M:%S.%f")
		util.DEBUG_LOG("Retrieved token %r, expires at %s" % (settings.TOKEN['hash'], settings.TOKEN['expires']))
		return


def getChanUrl(chan, force_rtmp=False, for_download=False, force_hls=False, force_mpeg=False):
	try:
		chan = int(chan)
		qualOptions = {}
		try:
			chanData = settings.CHANAPI[str(chan)]
		except:
			try:
				chanAPIURL = 'https://guide.smoothstreams.tv/api/api-qualities-new.php'
				settings.CHANAPI = json.loads(urllib.urlopen(chanAPIURL).read().decode("utf-8"))
				chanData = settings.CHANAPI[str(chan)]
			except:
				chanData = []
		for i in chanData:
			if i['id'] == '3': qualOptions['720'] = 'q'+i['stream']
			elif i['id'] == '4': qualOptions['540'] = 'q'+i['stream']
			elif i['id'] == '5': qualOptions['360'] = 'q'+i['stream']
		try:
			if util.getSetting("high_def", 0) == 0:
				quality = "720"  # HD - 2800k
			elif util.getSetting("high_def", 0) == 1:
				quality = "540"  # LD - 1250k
			elif util.getSetting("high_def", 0) == 2:
				quality = "360"  # Mobile - 400k ( Not in settings)
			else:
				quality = "360"
		except:  # backwards compatibility
			util.setSetting("high_def", 0)
			quality = "720"
		sanitizedQuality = 'q1'
		if quality in qualOptions:
			sanitizedQuality = qualOptions[quality]
	except:
		sanitizedQuality = 'q1'
	service = services[serviceIDX()]
	region = util.getSetting('server_region', 'North America')
	server = servers['NA Mix']
	try:
		if region == 'North America':
			server = servers[util.getSetting('server_r0', 'NA Mix')]
		elif region == 'Europe':
			server = servers[util.getSetting('server_r1', 'Euro Mix')]
		elif region == 'Asia':
			server = servers[util.getSetting('server_r2', 'Asia Mix')]
	except:
		# unknown server detected, using NA mix
		util.setSetting('server_region', 'North America')
		util.setSetting('server_r0', 'NA Mix')
		util.setSetting('server_r1', 'Euro Mix')
		util.setSetting('server_r2', 'Asia Mix')
		pass
	try:
		# second check in case  an index somehow gets through the above
		i = int(server)
		server = servers['NA Mix']
		util.setSetting('server_region', 'North America')
		util.setSetting('server_r0', 'NA Mix')
		util.setSetting('server_r1', 'Euro Mix')
		util.setSetting('server_r2', 'Asia Mix')
	except:
		pass

	# server = service['servers'][util.getSetting(service['servers_sett'],0)]

	check_token()
	credentials = settings.TOKEN['hash']
	if not credentials: return
	if for_download:
		util.DEBUG_LOG('Using {0}'.format(service['name']))
		chan_template = 'https://{server}:{port}/{site}/ch{channel:02d}{quality}.stream/playlist.m3u8?wmsAuthSign={hash}'

		url = chan_template.format(
			server=server,
			port=service['hls_port'],
			site=service['site'],
			channel=chan,
			quality=sanitizedQuality,
			hash=credentials
		)
		return url
	type = int(util.getSetting("server_type", 1))
	if force_hls:
		type = 1
	elif force_rtmp:
		type = 0
	elif force_mpeg:
		type = 2
	if type == 0:  # and not server.get('temp_force_hls'):
		util.DEBUG_LOG('Using {0}'.format(service['name']))
		chan_template = 'rtmp://{server}:{port}/{site}/ch{channel:02d}{quality}.stream?wmsAuthSign={hash}&user_agent={user_agent}'

		if not for_download: chan_template += ' live=1 timeout=20'
		url = chan_template.format(
			server=server,
			port=service['rtmp_port'],
			site=service['site'],
			channel=chan,
			quality=sanitizedQuality,
			user_agent=urllib.parse.quote(util.USER_AGENT.replace('/', '_')),
			hash=credentials
		)

	elif type == 2:
		util.DEBUG_LOG('Using {0}'.format(service['name']))
		chan_template = 'https://{server}:{port}/{site}/ch{channel:02d}{quality}.stream/mpeg.2ts?wmsAuthSign={hash}'

		url = chan_template.format(
			server=server,
			port=service['hls_port'],
			site=service['site'],
			channel=chan,
			quality=sanitizedQuality,
			hash=credentials
		)

	else:
		util.DEBUG_LOG('Using {0}'.format(service['name']))
		# Kodi version check for SSL
		kodi_version = int(xbmc.getInfoLabel('System.BuildVersion').split('.', 1)[0])
		chan_template = 'https://{server}:{port}/{site}/ch{channel:02d}{quality}.stream/playlist.m3u8?wmsAuthSign={hash}'

		url = chan_template.format(
			server=server,
			port=service['hls_port'],
			site=service['site'],
			channel=chan,
			quality=sanitizedQuality,
			hash=credentials
		)

	return url

def getCustomUrl(chan, streamType=None, quality=None):
	service = services[serviceIDX()]
	server_sett = 'server_r' + str(util.getSetting('server_region', 0))
	server = util.getSetting(server_sett)
	server = servers[server_sett][int(server)]
	# server = service['servers'][util.getSetting(service['servers_sett'],0)]
	try:
		if not quality:
			if util.getSetting("high_def", 0) == 0:
				quality = "q1"  # HD - 2800k
			elif util.getSetting("high_def", 0) == 1:
				quality = "q2"  # LD - 1250k
			elif util.getSetting("high_def", 0) == 2:
				quality = "q3"  # Mobile - 400k ( Not in settings)
			else:
				quality = "q1"
	except:  # backwards compatibility
		util.setSetting("high_def", 0)
		quality = "q1"
	check_token()
	credentials = settings.TOKEN['hash']
	if not credentials: return
	if streamType == 'rtmp' or (not streamType and util.getSetting("server_type", 0) == 0):  # and not server.get('temp_force_hls'):
		chan_template = 'rtmp://{server}:{port}/{site}/ch{channel:02d}{quality}.stream?wmsAuthSign={hash}&user_agent={user_agent}'

		chan_template += ' live=1 timeout=20'
		url = chan_template.format(
			server=server,
			port=service['rtmp_port'],
			site=service['site'],
			channel=chan,
			quality=quality,
			user_agent=urllib.parse.quote(util.USER_AGENT.replace('/', '_')),
			hash=credentials
		)

	else:
		chan_template = 'https://{server}:{port}/{site}/ch{channel:02d}{quality}.stream/playlist.m3u8?wmsAuthSign={hash}'

		url = chan_template.format(
			server=server,
			port=service['hls_port'],
			site=service['site'],
			channel=chan,
			quality=quality,
			hash=credentials
		)

	return url

# will require modification
# def averageList(self, lst):
#     util.DEBUG_LOG(repr(lst))
#     avg_ping = 0
#     avg_ping_cnt = 0
#     for p in lst:
#         try:
#             avg_ping += float(p)
#             avg_ping_cnt += 1
#         except:
#             util.DEBUG_LOG("Couldn't convert %s to float" % repr(p))
#     return avg_ping / avg_ping_cnt
#
# def testServers(self, update_settings=True):
#     if not util.getSetting("auto_server",False): return None
#
#     service = self.service
#
#     util.DEBUG_LOG("Original server: {0} - {1}".format(service['servers'][util.getSetting(service['servers_sett'],0)]['host'],util.getSetting(service['servers_sett'],0)))
#
#     import re, subprocess
#     res = None
#     ping = False
#     with util.xbmcDialogProgress('Testing servers...') as prog:
#         for i, server in enumerate(service['servers']):
#             if not prog.update( int((100.0/len(service['servers'])) * i), 'Testing servers...', '', server['name']):
#                 util.setSetting("auto_server", False)
#                 return
#             ping_results = False
#             try:
#                 if xbmc.getCondVisibility('system.platform.windows'):
#                     p = subprocess.Popen(["ping", "-n", "4", server['host']], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
#                 else:
#                     p = subprocess.Popen(["ping", "-c", "4", server['host']], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#                 ping_results = re.compile("time=(.*?)ms").findall(p.communicate()[0])
#             except:
#                 util.DEBUG_LOG("Platform doesn't support ping. Disable auto server selection")
#                 util.setSetting("auto_server", False)
#                 return None
#
#             if ping_results:
#                 util.DEBUG_LOG("Server %s - %s: n%s" % (i, server['host'], repr(ping_results)))
#                 avg_ping = self.averageList(ping_results)
#                 if avg_ping != 0:
#                     if avg_ping < ping or not ping:
#                         res = i
#                         ping = avg_ping
#                         if update_settings:
#                             util.DEBUG_LOG("Updating settings")
#                             util.setSetting("server", str(i))
#                 else:
#                     util.DEBUG_LOG("Couldn't get ping")
#
#     if res != None:
#         xbmcgui.Dialog().ok('Done','Server with lowest ping ({0}) set to:'.format(ping),'',service['servers'][res]['name'])
#     util.setSetting("auto_server", False)
#     util.DEBUG_LOG("Done %s: %s" % (service['servers'][res]['name'], ping))
#     return res
