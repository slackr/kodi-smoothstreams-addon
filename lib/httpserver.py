from __future__ import absolute_import, division, unicode_literals
import xbmcplugin,xbmcaddon
from .smoothstreams import authutils, proxyutils
import os, xbmc
from . import util, settings
from xbmcaddon import Addon

from six.moves.BaseHTTPServer import BaseHTTPRequestHandler
from six.moves.BaseHTTPServer import HTTPServer
# from six.moves.SocketServer import ThreadingMixIn
from threading import Thread

jsonGetPVR = '{"jsonrpc":"2.0", "method":"Settings.GetSettingValue", "params":{"setting":"pvrmanager.enabled"}, "id":1}'
jsonSetPVR = '{"jsonrpc":"2.0", "method":"Settings.SetSettingValue", "params":{"setting":"pvrmanager.enabled", "value":%s},"id":1}'
jsonNotify = '{"jsonrpc":"2.0", "method":"GUI.ShowNotification", "params":{"title":"PVR", "message":"%s","image":""}, "id":1}'


__addon__ = xbmcaddon.Addon()

ADDONNAME = __addon__.getAddonInfo('name')
ADDONID = __addon__.getAddonInfo('id')

__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__cwd__ = __addon__.getAddonInfo('path')
__version__ = __addon__.getAddonInfo('version')
debug = __addon__.getSetting("debug")


MyAddon = Addon(ADDONID)
PORT_NUMBER = int(62555)


class http_server:
	def __init__(self, portNumber):
		self.portNumber = portNumber
		util.LOG('INIT HTTP SERVER')
		try:
			try:
				a = settings.TOKEN
			except:
				settings.init()
				authutils.load_token()
				authutils.check_token()
			serverThread = Thread(target=self.start_server)
			serverThread.daemon = True  # Do not make us wait for you to exit
			serverThread.start()
			self.waitForAbort()
			util.LOG('killing iptv')
			# proxyutils.Proxy().disableAddons()
		except:
			util.LOG('Http server died')
			pass

	def waitForAbort(self, sec_float=0):
		if sec_float:
			ms = sec_float * 1000
			ct = 0
			while not xbmc.Monitor().abortRequested() and ct < ms:
				xbmc.sleep(100)
				ct += 100
		else:
			while not xbmc.Monitor().abortRequested():
				xbmc.sleep(100)

	def start_server(self):
		try:
			server = HTTPServer(('', self.portNumber), myHandler)
			util.LOG('HTTP Proxy started')
			authutils.check_token()
			pr = proxyutils.Proxy()
			pr.build_playlist()
			pr.dl_epg(source=1)
			pr.enableAddons()
			# pr.restartAddon()
			del pr

			server.serve_forever()
		except:
			util.ERROR('HTTP Proxy failed to start!')



class myHandler(BaseHTTPRequestHandler):
	def do_GET(self):
		self.proxy = proxyutils.Proxy()

		args = {}
		request_file = self.path[1:]
		if '?' in request_file:
			request_file = request_file.split('?')[0]
			raw_args = self.path[1:].split('?')[1]

			# split multiple args into a list
			split_args = raw_args.split('&')

			for i in split_args:
				# split each arg into its two parts
				args[i.split('=')[0]] = i.split('=')[1]

		if request_file.lower() == 'playlist.m3u8':
			if args.get('ch'):
				if not authutils.check_token(): return
				sanitized_channel = ("0%d" % int(args.get('ch'))) if int(
					args.get('ch')) < 10 else args.get('ch')
				url = authutils.getChanUrl(sanitized_channel)
				if util.getSetting("server_type", 0) == 1:
					output_url = self.proxy.create_hls_channel_playlist(url)
					self.send_response(200)
					self.send_header("Content-type", "application/x-mpegURL")
				elif util.getSetting("server_type", 0) == 0:
					output_url = url
					self.send_response(302)
					self.send_header("Content-type", "rtmp/mp4")
				else:
					output_url = url
					self.send_response(302)
					self.send_header("Content-type", "video/mp2t")
				util.LOG("returning %s" % output_url)
				self.send_header("Access-Control-Allow-Origin", "*")
				self.end_headers()
				self.wfile.write(output_url.encode('utf-8'))
				self.wfile.close()
				self.finish()
			else:
				playlist = self.proxy.build_playlist()
				util.LOG("All channels playlist was requested.")
				self.send_response(200)
				self.send_header("Content-type", "application/x-mpegURL")
				self.end_headers()
				self.wfile.write(playlist.encode('utf-8'))
				self.wfile.close()
				self.finish()

		if request_file.lower() == 'mpeg.2ts':
			if args.get('ch'):
				if not authutils.check_token(): return
				sanitized_channel = ("0%d" % int(args.get('ch'))) if int(
					args.get('ch')) < 10 else args.get('ch')
				url = authutils.getChanUrl(sanitized_channel)
				output_url = url
				self.send_response(302)
				# self.send_header("Content-type", "video/mp2t")
				util.LOG("returning %s" % output_url)
				# self.send_header("Access-Control-Allow-Origin", "*")
				self.send_header('Location', output_url)
				self.end_headers()
				# self.wfile.write(output_url)
				# self.wfile.close()
				self.finish()
			else:
				playlist = self.proxy.build_playlist()
				util.LOG("All channels playlist was requested.")
				self.send_response(200)
				self.send_header("Content-type", "application/x-mpegURL")
				self.end_headers()
				self.wfile.write(playlist.encode('utf-8'))
				self.wfile.close()
				self.finish()

		if request_file.lower() == 'refresh.m3u8':
			self.proxy.updatePVRSettings()
			self.proxy.dl_epg()
			self.proxy.restartAddon()

		if request_file.lower() == 'epg.xml':
			self.proxy.dl_epg(source=1)
			# shutil.copy(os.path.join(util.PROFILE, 'epg.xml'), os.path.join(os.path.join(util.PROFILE,'..','pvr.iptvsimple','xmltv.xml.cache')))
			f = open(os.path.join(util.PROFILE, 'epg.xml'), 'rb')
			self.send_response(200)
			self.send_header("Content-type", "application/xml")
			self.end_headers()
			# self.wfile.write('<?xml version="1.0" encoding="UTF-8"?>'.rstrip('\r\n'))
			self.wfile.write(f.read().encode('utf-8'))
			self.wfile.close()
			self.finish()

		# if '/playLiveAddon/' in self.path:
		# 	streamId = self.path[2:].split('/playLiveAddon/')[1].strip()
		# 	url = self.server.vaderClass.build_stream_url(streamId)
		# 	self.send_response(302)
		# 	self.send_header('Location', url)
		# 	self.end_headers()
		# 	self.finish()
		#
		# if '/playLive/' in self.path:
		# 	streamId = self.path[2:].split('/playLive/')[1].strip()
		# 	url = self.server.vaderClass.build_stream_url(streamId, pvr=True)
		# 	self.send_response(302)
		# 	self.send_header('Location', url)
		# 	self.end_headers()
		# 	self.finish()
		#
		# if '/getAddonID' in self.path:
		# 	self.send_response(200)
		# 	self.send_header("Content-type", "text/html")
		#
		# 	self.end_headers()
		# 	self.wfile.write(ADDONID)
		#
		# 	self.wfile.close()
		#
		# if '/getCategories' in self.path:
		# 	self.send_response(200)
		# 	self.send_header("Content-type", "text/html")
		#
		# 	self.end_headers()
		# 	self.wfile.write(self.server.vaderClass.get_epg_categories())
		#
		# 	self.wfile.close()
		#
		# if '/getStreams' in self.path:
		# 	self.send_response(200)
		# 	self.send_header("Content-type", "text/html")
		#
		# 	self.end_headers()
		# 	streams = json.dumps(self.server.vaderClass.get_valid_streams())
		# 	self.wfile.write(streams)
		#
		# 	self.wfile.close()
		#
		#
		# if '/getCreds' in self.path:
		# 	self.send_response(200)
		# 	self.send_header("Content-type", "text/html")
		# 	username = self.server.vaderClass.username
		# 	password = self.server.vaderClass.password
		# 	data = {}
		# 	data['username'] = username
		# 	data['password'] = password
		# 	self.end_headers()
		# 	dataDump = json.dumps(data)
		# 	self.wfile.write(dataDump)
		#
		# 	self.wfile.close()


	def do_HEAD(self):
		self.send_response(200)
		self.send_header('Content-type', 'video/mp2t')
		self.end_headers()
		self.finish()


if __name__ == "__main__":
	server = http_server(9696)