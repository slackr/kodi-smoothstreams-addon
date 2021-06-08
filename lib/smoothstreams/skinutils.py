import xbmcgui

from lib import util

orange = 'FFF36523'
skyBlue = 'FF12A0C7'
backBlue = 'FF0E597E'
def setColours():
	focus = xbmcgui.Window(10000).getProperty('script-smoothstreams-v3.colour.select.focus')
	if focus and focus != '':
		util.setSetting('colour_focus', focus)
	else:
		focus = util.getSetting('colour_focus', 'FF12A0C7')
	util.setGlobalProperty('colour.focus', focus)
	util.setGlobalProperty('colour.progress', focus)

	back = xbmcgui.Window(10000).getProperty('script-smoothstreams-v3.colour.select.background')
	if back and back != '':
		util.setSetting('colour_background', back)
	else:
		back = util.getSetting('colour_background', 'FF0E597E')
	util.setGlobalProperty('colour.background', back)