from lib import util
import xbmcgui, os, xbmc, xbmcvfs
# *Note, choices are (author, changelog, description, disclaimer, fanart. icon, id, name, path, profile, stars, summary, type, version)
def versionNotification():
	changeLogReq = False
	if 'dev' in util.ADDON_ID:
		text = "Warning: DEV Version, bugs are to be expected."
		xbmcgui.Dialog().ok('SmoothStreams', text)
	if os.path.isfile(os.path.join(util.PROFILE,'version_seen.txt')):
		with open (os.path.join(util.PROFILE,'version_seen.txt'), 'r' )as f:
			version = f.read()
		if version != util.ADDON.getAddonInfo('version'):
			changeLogReq = True
		with open(os.path.join(util.PROFILE, 'version_seen.txt'), 'w')as f:
			f.write(util.ADDON.getAddonInfo('version'))

	# existing build detection
	elif os.path.isfile(os.path.join(util.PROFILE,'last_mode')) or os.path.isfile(os.path.join(xbmcvfs.translatePath(util.ADDON.getAddonInfo('profile')),'last_mode')):
		with open(os.path.join(util.PROFILE, 'version_seen.txt'), 'w')as f:
			f.write(util.ADDON.getAddonInfo('version'))
		changeLogReq = True

	else:
		# fresh build
		if xbmcgui.Dialog().yesno('SmoothStreams', 'Welcome to Smoothstreams, would you like to read the brief tutorial?'):
			xbmcgui.Dialog().ok('SmoothStreams', 'To open the side menu either cursor to the left or press "M". The context menu can be found by right clicking on an item or pressing and holding select/enter. These menus allow you to change your view type and access the settings.')
			xbmcgui.Dialog().ok('SmoothStreams', 'Different EPG options are available in the add-on settings.')
			xbmcgui.Dialog().ok('SmoothStreams', 'If your stream keeps cutting out reguarly try a different server from the options.')
			xbmcgui.Dialog().ok('SmoothStreams', 'Channels can be selected at any time by using left-click, enter, select or typing the number in numerically.')
		with open(os.path.join(util.PROFILE, 'version_seen.txt'), 'w')as f:
			f.write(util.ADDON.getAddonInfo('version'))

	if changeLogReq:
		if xbmcgui.Dialog().yesno('SmoothStreams', 'Addon has been updated, would you like to see the changelog?'):
			text = util.ADDON.getAddonInfo('changelog')
			xbmcgui.Dialog().ok('SmoothStreams', text)
		text = util.ADDON.getAddonInfo('disclaimer')
		if text:
			xbmcgui.Dialog().ok('SmoothStreams', text)