import sublime
import sublime_plugin
import json
import subprocess
import re
import os
import plistlib
import collections
import shutil
import webbrowser
from datetime import datetime, timedelta
from os.path import basename
from io import StringIO
from zipfile import ZipFile
from urllib.request import urlopen
from urllib.request import urlretrieve

PLUGIN_FOLDER = os.path.dirname(os.path.realpath(__file__))
PLUGIN_NAME = "Titanium"
SETTINGS_FILE = PLUGIN_NAME + ".sublime-settings"
SETTINGS_PREFIX = PLUGIN_NAME.lower() + '_'

settings = sublime.load_settings(SETTINGS_FILE)

my_session_settings = {}

def sessionSetting(name, value = 'Nopennada'):
	realName = name + '_'+str(sublime.active_window().id())
	if value == "Nopennada":
		if (realName in my_session_settings):
			return my_session_settings[realName]
		else:
			return None
	else:
		my_session_settings[realName] = value

def sessionHasSetting(name):
	realName = name + '_'+str(sublime.active_window().id())
	return (realName in my_session_settings)
def sessionRemoveSetting(name):
	realName = name + '_'+str(sublime.active_window().id())
	del my_session_settings[realName]



def get_setting(key, default=None, view=None):
	try:
		if view == None:
			view = sublime.active_window().active_view()
		s = view.settings()
		if s.has(SETTINGS_PREFIX + key):
			print('get_setting from view : ' + key + ',' + settings.get(key, default))
			return s.get(SETTINGS_PREFIX + key)
	except:
		pass
	if settings.has(key):
		print('get_setting: ' + key + ',' + settings.get(key, default))
		return settings.get(key, default)
	else:
		print('get_setting: ' + key + ',' + default)
		return default

def copyFile(src, dest):
	try:
		print ("copying " + src + " to " +  dest)
		shutil.copy2(src, dest)
	# eg. src and dest are the same file
	except shutil.Error as e:
		print('Error: %s' % e)
	# eg. source or destination doesn't exist
	except IOError as e:
		print('Error: %s' % e.strerror)

def plugin_loaded():
	global settings
	settings = sublime.load_settings(SETTINGS_FILE)

class TitaniumCommand(sublime_plugin.WindowCommand):

	def plistStringFromProvFile(self, path):
		beginToken = '<?xml'
		endToken = '</plist>'
		f = open(path, "rb")
		data =  str(f.read())
		f.close()
		begin = data.find(beginToken)
		end = data.find(endToken) + len(endToken) 
		return data[begin:end]

	def getUUIDAndName(self, certPath):
		plistString = self.plistStringFromProvFile(certPath).replace('\\n', "")
		plist = plistlib.readPlistFromBytes(bytes(plistString, 'utf-8'))
		return [plist['UUID'],plist['TeamName'], plist['TeamIdentifier'][0]]

	def copyProvisioningProfile(self, certPath, certName):
		dest = os.path.join(os.path.expanduser('~/Library/MobileDevice/Provisioning Profiles'), certName + '.mobileprovision')
		if (not os.path.isfile(dest)):
			copyFile(certPath, dest)

	def updateIOsBuildInTiApp(self):
		#update build number
		tiappPath = os.path.join(self.project_folder, "tiapp.xml")
		if (os.path.isfile(tiappPath)):
			f2 = open(tiappPath, encoding='utf-8', mode='r')
			tiapp = f2.read()
			f2.close()
			m = re.search('(?<=<key>CFBundleVersion<\/key>)(\s*<string>)([\d]*)(?=<\/string>)',tiapp)
			if (m != None):
				version = int(m.group(2)) + 1
				print ('updating tiapp CFBundleVersion to ' + str(version))
				tiapp = re.sub('<key>CFBundleVersion</key>\s*<string>[\d]*</string>', '<key>CFBundleVersion</key><string>' + str(version) + '</string>',tiapp)
				f2 = open(tiappPath, encoding='utf-8', mode='w')
				f2.write(tiapp)
				f2.close()
		else:
			print ("tiapp.xml doesnt exist: " + tiappPath)

	def updateAndroidBuildInTiApp(self):
		#update build number
		tiappPath = os.path.join(self.project_folder, "tiapp.xml")
		if (os.path.isfile(tiappPath)):
			f2 = open(tiappPath, encoding='utf-8', mode='r')
			tiapp = f2.read()
			f2.close()
			m = re.search('(?<=android:versionCode=")([\d]*)(?=")',tiapp)
			if (m != None):
				version = int(m.group(1)) + 1
				print ('updating tiapp android:versionCode to ' + str(version))
				tiapp = re.sub('(?<=android:versionCode=")[\d]*(?=")', str(version),tiapp)
				f2 = open(tiappPath, encoding='utf-8', mode='w')
				f2.write(tiapp)
				f2.close()
		else:
			print ("tiapp.xml doesnt exist: " + tiappPath)

	def handleError(self, error):
		if (error is not None):
			print(error)
		sublime.log_commands(True)
		sublime.active_window().run_command("show_panel", {"panel": "console", "toggle": True})

	def select_most_recent_command(self, select):
		if select < 0:
			return

		titaniumMostRecents = sessionSetting('titaniumMostRecents')
		titaniumMostRecent = sessionSetting('titaniumMostRecent')
		recent = titaniumMostRecents[select]
		titaniumMostRecent = recent[-1]
		sessionSetting('titaniumMostRecent', titaniumMostRecent)
		titaniumMostRecents.remove(recent)
		titaniumMostRecents.appendleft(recent)
		self.window.run_command("exec", {"cmd": titaniumMostRecent})


	def runProjectCommand(self):
		if (not self.isTitaniumProject):
			if (self.command):
				self.window.run_command("build", {"variant": self.command})
			else:
				self.window.run_command("build")
			return
		if self.command == 'clean':
			self.window.run_command("exec", {"cmd": [self.node, self.cli, "clean", "--no-colors", "--project-dir", self.project_folder]})
		else:
			self.project_sdk = self.get_project_sdk_version()
			self.pick_platform()


	def run(self, *args, **kwargs):
		print(kwargs)
		self.command = None
		if 'command' in kwargs:
			self.command = kwargs['command']

		if (sessionHasSetting('titaniumMostRecent') and self.command == 'titaniumMostRecent'):
			self.window.run_command("exec", {"cmd": sessionSetting('titaniumMostRecent')})
			return

		titaniumMostRecents = sessionSetting('titaniumMostRecents')
		print(titaniumMostRecents)
		if (titaniumMostRecents and 'titaniumMostRecents'  and self.command == 'titaniumMostRecents'):
			cmds = []
			for project,platform, target, options,cmd in titaniumMostRecents:
				cmds.append([os.path.basename(project) + ' / ' + platform + ' / ' + target, ' '.join(options)])
			self.show_quick_panel(cmds, self.select_most_recent_command)
			return

		folders = self.window.folders()
		self.node              = get_setting("nodejs", "/usr/local/bin/node")
		self.cli              = get_setting("titaniumCLI", "/usr/local/bin/titanium")
		self.android          = get_setting("androidSDK", "/opt/android-sdk") + "/tools/android"
		self.loggingLevel     = get_setting("loggingLevel", "debug")
		self.iosVersion       = str(get_setting("iosVersion", "unknown"))
		self.outputDir       = str(get_setting("outputDir", "release"))
		self.certsDir       = str(get_setting("iosCertsDir", "unknown"))
		self.defaultKeychain       = str(get_setting("iosKeychain", "unknown"))
		self.infoLoaded       = False
		self.isTitaniumProject = False	

		if len(folders) <= 0:
			self.show_quick_panel(["ERROR: Must have a project open"], None)
		else:
			if len(folders) == 1:
				self.multipleFolders = False
				self.project_folder = folders[0]
				if (os.path.isfile(os.path.join(self.project_folder, "tiapp.xml"))):
					self.isTitaniumProject = True 
				self.runProjectCommand()
				
			else:
				self.multipleFolders = True
				self.pick_project_folder(folders)

	def pick_project_folder(self, folders):
		folderNames = []
		for folder in folders:
			index = folder.rfind('/') + 1
			if index > 0:
				folderNames.append(folder[index:])
			else:
				folderNames.append(folder)

		# only show most recent when there is a command stored
		if sessionHasSetting('titaniumMostRecent'):
			folderNames.insert(0, 'most recent configuration')

		self.show_quick_panel(folderNames, self.select_project)

	def select_project(self, select):
		folders = self.window.folders()
		if select < 0:
			return

		# if most recent was an option, we need subtract 1
		# from the selected index to match the folders array
		# since the "most recent" option was inserted at the beginning
		if sessionHasSetting('titaniumMostRecent'):
			select = select - 1

		if select == -1:
			self.window.run_command("exec", {"cmd": sessionSetting('titaniumMostRecent')})
		else:
			self.project_folder = folders[select]
			if (os.path.isfile(os.path.join(self.project_folder, "tiapp.xml"))):
				self.isTitaniumProject = True 
			self.runProjectCommand()



	def pick_platform(self):
		self.preCmd = [self.node, self.cli, "--sdk", self.project_sdk, "--project-dir", self.project_folder]
		self.platforms = ["android", "ios", "mobileweb", "clean", "fontello"]

		# only show most recent when there are NOT multiple top level folders
		# and there is a command stored
		if self.multipleFolders == False and 'titaniumMostRecent' in globals():
			self.platforms.insert(0, 'most recent configuration')

		self.show_quick_panel(self.platforms, self.select_platform)

	def select_platform(self, select):
		if select < 0:
			return
		self.platform = self.platforms[select]

		if self.platform == "most recent configuration":
			self.window.run_command("exec", {"cmd": titaniumMostRecent})
		elif self.platform == "ios":
			self.targets = ["simulator", "simulator auto", "device", "device-adhoc", "dist-adhoc", "dist-appstore"]
			self.show_quick_panel(self.targets, self.select_ios_target)
		elif self.platform == "android":
			self.targets = ["emulator", "emulator auto", "device", "dist-adhoc", "dist-playstore"]
			self.show_quick_panel(self.targets, self.select_android_target)
		elif self.platform == "mobileweb":
			self.targets = ["development", "production"]
			self.show_quick_panel(self.targets, self.select_mobileweb_target)
		elif self.platform == "fontello":

			self.targets = ["open", "build"]
			self.fontelloConfigFiles = []
			for f in os.listdir(self.project_folder):
				if re.match(r'fontello_.*\.json', f):
					self.fontelloConfigFiles.append([(('.').join(f.split('.')[:-1])).split('_')[-1:][0], f])
			print(self.fontelloConfigFiles)
			options = self.fontelloConfigFiles[:]
			options.insert(0, ["create",""])
			if sessionHasSetting('fontelloCurrent'):
				fontello = sessionSetting('fontelloCurrent')
				print(fontello)
				if (datetime.now() - datetime.fromtimestamp(fontello[3])) > timedelta(hours = 20):
					sessionRemoveSetting('fontelloCurrent')
				else:
					options = [['open ' + fontello[0], fontello[1]], ['build ' + fontello[0], fontello[1]], 'other']
					self.fontelloConfigFile = [fontello[0], fontello[1]]
					self.fontelloSessionId = fontello[2]
					self.show_quick_panel(options, self.select_fontello_current)
					return
			print(options)
			self.show_quick_panel(options, self.select_fontello_config)
		else:  # clean project
			self.command = "clean"
			self.runProjectCommand()

	# Sublime Text 3 requires a short timeout between quick panels
	def show_quick_panel(self, options, done): 
		sublime.set_timeout(lambda: self.window.show_quick_panel(options, done), 10)
	
	# Sublime Text 3 requires a short timeout between quick panels
	def show_input_panel(self, hint, default, done): 
		sublime.set_timeout(lambda: self.window.show_input_panel(hint, default, done, None, None), 10)


	# get the current project's SDK from tiapp.xml
	def get_project_sdk_version(self):
		cmd = [self.node, self.cli, "project", "sdk-version", "--project-dir", self.project_folder, "--log-level", "error", "--output", "json"]
		print(" ".join(cmd))
		process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		result, error = process.communicate()
		info = json.loads(result.decode('utf-8'))
		print(info)
		return info

	def run_titanium(self, options=[]):
		cmd = self.preCmd +["build", "--platform", self.platform, "--log-level", self.loggingLevel, "--no-colors"]
		if (self.platform is "ios" and self.iosVersion is not "unknown" and self.iosVersion is not ""):
			options.extend(["--ios-version", self.iosVersion])
		cmd.extend(options)

		# save most recent command

		sessionSetting('titaniumMostRecent', cmd)

		titaniumMostRecents = sessionSetting('titaniumMostRecents')
		if (not titaniumMostRecents):
			titaniumMostRecents = collections.deque([[self.project_folder, self.platform, self.target, options, cmd]])
		else:
			titaniumMostRecents.appendleft([self.project_folder, self.platform, self.target, options, cmd])
			if (len(titaniumMostRecents) > 10):
				titaniumMostRecents.pop()
		sessionSetting('titaniumMostRecents', titaniumMostRecents)
		self.window.run_command("exec", {"cmd": cmd, "file_regex":"^(?:.*?Script\\sError\\sat\\s+(?:file:\/\/)?)([^:]+):(\\d+)(?::\"(.*?)\")?.*$"})

	#--------------------------------------------------------------
	# FONTELLO
	#--------------------------------------------------------------
	def filterPick(self, lines, regex):
		return [m.group() for m in (re.search(regex, l) for l in lines) if m]
		# matches = map(re.compile(regex).match, lines)
		# return [m.group(1) for m in matches if m]


	def extractFileFromZip(self, zipfile, fileZipPath, outputPath):
		# copy file (taken from zipfile's extract)
		source = zipfile.open(fileZipPath)
		target = open(outputPath, "wb")
		with source, target:
			shutil.copyfileobj(source, target)


	def generateIconicFont(self, configJSON, fontName):
		glyphs = []
		fileContent = "function Font(options) {\n\tthis.fontfamily = '" + fontName + "';\n\tthis.charcode = {\n"
		for glyph in configJSON["glyphs"]:
			if ("selected" not in glyph or glyph["selected"] == True):
				fileContent += "\t\t'" + glyph["css"] + "': " + hex(glyph["code"]) + ",\n"
		fileContent += "\t};\n}\nFont.prototype.getCharcode = function(options) {\n\treturn this.charcode[options];\n};\nmodule.exports = Font;"
		target = open(os.path.join(self.project_folder, "Resources", "fonts", "font_" + fontName + ".js"), encoding='utf-8', mode='w')
		target.write(fileContent)
		target.close()

	def buildFontelloFontForTi(self, fontName, fontConfigFile, fontelloSessionId):
		configPath = os.path.join(self.project_folder, fontConfigFile)
		zipPath = os.path.join("/tmp/", ".fontello.zip")

		curl = ["curl", "--silent", "--show-error", "--fail"]
		curl.extend(["--output", zipPath])
		curl.extend(["http://www.fontello.com/"+ fontelloSessionId + "/get"])
		print(' '.join(curl))
		subprocess.Popen(curl, stdout=subprocess.PIPE).communicate()[0].decode()
		zipfile = ZipFile(zipPath)
		filenames = zipfile.namelist()
		configFile = self.filterPick(filenames, ".*\/config\.json")[0]
		fontFile = self.filterPick(filenames, ".*\/font/.*\.ttf")[0]
		fontName = None
		if (configFile):
			print(configFile)
			self.extractFileFromZip(zipfile, configFile, configPath)
			file = open(configPath, encoding='utf-8', mode='r')
			configJSON = json.loads(file.read())
			fontName = configJSON["name"]
			self.generateIconicFont(configJSON, fontName)

		if (fontFile and fontName  is not None):
			self.extractFileFromZip(zipfile, fontFile, os.path.join(self.project_folder, "Resources", "fonts", fontName + ".ttf"))

	def createFontelloFont(self, name):
		print(name)
		fontConfigFileName =  "fontello_" + name + ".json"
		filePath = os.path.join(self.project_folder, fontConfigFileName)
		if (os.path.isfile(filePath)):
			sublime.message_dialog("the fontello font " + name + " alread exists")
		else:
			target = open(filePath, encoding='utf-8', mode='w')
			target.write('{\n\t"name": "' + name + '",\n\t"css_prefix_text": "",\n\t"css_use_suffix": false,\n\t"hinting": true,\n\t"units_per_em": 1000,\n\t"ascent": 850\n}')
			target.close()
		self.fontelloConfigFile = [name, fontConfigFileName]
		self.run_fontello_command("open")

	def run_fontello_command(self, cmd):
		if not hasattr(self, 'fontelloSessionId'):
			curl = ["curl", "--silent", "--show-error", "--fail", "-H", "Accept: application/json", "--form"]
			curl.extend(["config=@" + os.path.join(self.project_folder,self.fontelloConfigFile[1])])
			curl.extend(["http://fontello.com"])
			print(' '.join(curl))
			self.fontelloSessionId = subprocess.Popen(curl, stdout=subprocess.PIPE).communicate()[0].decode()
			
			sessionSetting('fontelloCurrent', [
				self.fontelloConfigFile[0],
				self.fontelloConfigFile[1],
				self.fontelloSessionId,
				int(datetime.now().strftime("%s"))
			])
			print(sessionSetting('fontelloCurrent'))
		if(cmd == 'open'):
			webbrowser.open_new_tab('http://fontello.com/'+self.fontelloSessionId)
		elif(cmd == 'build'):
			self.buildFontelloFontForTi(self.fontelloConfigFile[0],
				self.fontelloConfigFile[1],
				self.fontelloSessionId)

	def select_fontello_current(self, select):
		if select < 0:
			return
		print(select)
		if select == 0:
			self.select_fontello_command(1)
		elif select == 1:
			self.select_fontello_command(2)
		else: #other
			options = self.fontelloConfigFiles[:]
			options.insert(0, ["create",""])
			self.show_quick_panel(options, self.select_fontello_config)


	def select_fontello_command(self, select):
		if select < 0:
			return
		if select == 0:
			self.show_input_panel('Enter the font name:', '', self.createFontelloFont)
		elif select == 1:
			self.run_fontello_command('open')
		elif select == 2:
			self.run_fontello_command('build')


	def select_fontello_config(self, select):
		if select < 0:
			return
		elif select == 0:
			self.select_fontello_command(0)
		else:
			self.fontelloConfigFile = self.fontelloConfigFiles[select-1]
			self.show_quick_panel(self.targets, self.select_fontello_target)

	def select_fontello_target(self, select):
		if select < 0:
			return
		self.target = self.targets[select]
		self.run_fontello_command(self.target)

	#--------------------------------------------------------------
	# MOBILE WEB
	#--------------------------------------------------------------

	def select_mobileweb_target(self, select):
		if select < 0:
			return

		self.run_titanium(["--deploy-type", self.targets[select]])

	#--------------------------------------------------------------
	# ANDROID
	#--------------------------------------------------------------

	def select_android_target(self, select):
		if select < 0:
			return
		self.target = self.targets[select]
		if (self.target == "emulator auto"):
			self.run_titanium([])
		elif (self.target == "emulator"):
			self.load_android_info()
			self.avds= []
			print(self.simulators)
			for simulator in self.simulators:
				if "target" in simulator:
					self.avds.append([simulator['name'], simulator['target']])
			self.show_quick_panel(self.avds, self.select_android_avd)
		elif(self.target == "dist-adhoc"):
			self.updateAndroidBuildInTiApp()
			options = ["--target", 'device', "--output-dir", os.path.join(self.project_folder,self.outputDir)]
			options.extend(['--deploy-type', "test"])
			options.extend(['--build-only'])
			self.run_titanium(options)
		elif(self.target == "dist-playstore"):
			self.updateAndroidBuildInTiApp()
			certsPath = os.path.join(self.project_folder, self.certsDir)
			options = ["--target", self.target, "--output-dir", os.path.join(self.project_folder,self.outputDir)]
			options.extend(["--store-password", get_setting("android.store-password", "")])
			options.extend(["--alias", get_setting("android.alias", "")])
			options.extend(['--keystore',  os.path.join(certsPath, get_setting("android.keystore", "android.keystore"))])
			self.run_titanium(options)
		else:
			self.run_titanium(["--target", self.target])

	def select_android_avd(self, select):
		if select < 0:
			return
		self.run_titanium(["--" + self.avdCmd, self.avds[select][0]])

	#--------------------------------------------------------------
	# IOS
	#--------------------------------------------------------------

	def select_ios_target(self, select):
		if select < 0:
			return
		self.target = self.targets[select]
		if self.target == "simulator":
			self.load_ios_info()
			self.simtype= []
			for simulator in self.simulators:
				if ('id' in simulator):
					self.simtype.append(simulator['id'])
				else:
					self.simtype.append([simulator['name'], simulator['udid']])
			self.show_quick_panel(self.simtype, self.select_ios_simtype)
		elif self.target == "simulator auto":
			self.run_titanium([])
		else:
			self.families = ["iphone", "ipad", "universal"]
			self.show_quick_panel(self.families, self.select_ios_family)

	def select_ios_simtype(self, select):
		if select < 0:
			return
		deviceId =self.simtype[select]
		if isinstance(deviceId, list):
			print(deviceId)
			deviceId =  deviceId[1]
			print(deviceId)
			self.run_titanium(["--device-id", deviceId, "--device-family", "universal"])
		else:
			simulatorType = re.match('iphone|ipad', deviceId, re.IGNORECASE).group().lower()
			self.run_titanium(["--sim-type", simulatorType, "--device-id", deviceId])


	def select_ios_family(self, select):
		if select < 0:
			return
		self.family = self.families[select]
		if (self.certsDir is not "unknown"):
			certsPath = os.path.join(self.project_folder, self.certsDir)
			if (self.target == "device"):
				certPath = os.path.join(certsPath, "development.mobileprovision")
			elif (self.target == "dist-appstore"):
				certPath = os.path.join(certsPath, "appstore.mobileprovision")
			else:
				certPath = os.path.join(certsPath, "distribution.mobileprovision")
			try:
				self.profile, self.teamname, self.teamid = self.getUUIDAndName(certPath)
				self.teamfullname = self.teamname + " (" + self.teamid + ")"
				self.copyProvisioningProfile(certPath, self.profile)
				if (self.target != "device"):
					self.build_ios_with_profile()
					return
			except Exception as e: 
				self.handleError(e)
				return

		self.load_ios_info()
		if (self.defaultKeychain is not "unknown" and self.defaultKeychain in self.keychains):
			self.handle_ios_keychain(self.defaultKeychain)
		else:
			if (len(self.keychainNames) > 1):
				self.show_quick_panel(self.keychainNames, self.select_ios_keychain)
			else:
				self.select_ios_keychain(0)

	def get_ios_certs_from_keychain(self):
		propName = 'distribution'
		if (self.target=='device'):
			propName = 'developer'
		certs = self.keychain[propName]
		self.certs = []
		for obj in certs:
			if (isinstance(obj, str)):
				self.certs.append(obj)
			elif (obj['invalid'] == False):
				self.certs.append(obj['name'])


	def handle_ios_keychain(self, name):
		self.load_ios_info()
		self.keychain = self.keychains[name]
		self.get_ios_certs_from_keychain()
		if (len(self.certs) > 1):
			self.show_quick_panel(self.certs, self.select_ios_cert)
		else:
			self.select_ios_cert(0)

	def select_ios_keychain(self, select):
		if select < 0:
			return
		self.load_ios_info()
		self.handle_ios_keychain(self.keychainNames[select])

	def select_ios_cert(self, select):
		if select < 0:
			return
		self.load_ios_info()
		self.cert = self.certs[select]
		
		if (self.profile is not None):
			self.build_ios_with_profile()
		else:
			if (len(self.profiles) > 1):
				self.show_quick_panel(self.profiles, self.select_ios_profile)
			else:
				self.select_ios_profile(0)

	def select_ios_profile(self, select):
		if select < 0:
			return
		self.teamfullname, self.profile = self.profiles[select]
		self.build_ios_with_profile()

	def build_ios_with_profile(self):
		target = self.target
		if(self.target == "device-adhoc"):
			target = 'dist-adhoc'
		options = ["--target", target, "--pp-uuid", self.profile, "--device-family", self.family]
		if(self.target == "device-adhoc"):
			options.extend(["--deploy-type", 'development'])
		if self.target == "device":
			options.extend(["--developer-name", self.cert])
		else:
			options.extend(["--distribution-name", self.teamfullname])
		if self.target == "dist-adhoc":
			options.extend(["--deploy-type", 'test'])
		if self.target == "dist-adhoc" or target == "dist-appstore":
			self.updateIOsBuildInTiApp();
		if target == "dist-adhoc" or target == "device":
			options.extend(["--output-dir", os.path.join(self.project_folder,self.outputDir), '--device-id', 'all'])
		self.run_titanium(options)

	def load_android_info(self):
		if(self.infoLoaded):
			return
		self.infoLoaded = True
		process = subprocess.Popen( self.preCmd + ["info", "--types", "android", "--log-level", "error", "--output", "json"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		result, error = process.communicate()
		info = json.loads(result.decode('utf-8'))
		print (info)
		if "android" in info:
			android = info['android'];
			if "emulators" in android:
				self.avdCmd = "device-id"
				self.simulators = android["emulators"]
			elif "avds" in android:
				self.avdCmd = "avd-id"
				self.simulators = android["avds"]

	def load_ios_info(self):
		if(self.infoLoaded):
			return
		self.infoLoaded = True
		process = subprocess.Popen( self.preCmd + ["info", "--types", "ios", "--log-level", "error", "--output", "json"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		result, error = process.communicate()
		info = json.loads(result.decode('utf-8'))
		# print (info)
		if "ios" in info:
			ios = info['ios'];
			if "certs" in ios:
				for target, c in list(ios["certs"].items()):
					if target == "wwdr" or (target == "devNames" and self.target != "device") or (target == "distNames" and self.target == "device"):
						continue
					keychains = []
					self.keychains = {}
					for keychain in c:
						keychains.append(keychain)
						self.keychains[keychain] = c[keychain]
					self.keychainNames = keychains
			if "provisioningProfiles" in ios:
				for target, p in list(ios["provisioningProfiles"].items()):
					# TODO: figure out what to do with enterprise profiles
					if (target == "development" and self.target == "device") or (target == "distribution" and self.target == "dist-appstore") or (target == "adhoc" and self.target == "dist-adhoc"):
						l = []
						for profile in p:
							l.append([profile['name'], profile['uuid']])
						self.profiles = l
			if "simulators" in ios:
				print("test1" )
				selectedXcode = ios["selectedXcode"]
				print(selectedXcode)
				if ("sims" in selectedXcode):
					print("test2" )
					sdks = selectedXcode["sdks"]
					sims = selectedXcode["sims"]

					self.simulators = ios["simulators"][selectedXcode['sims'][0]]
					print("toto" + str(self.simulators))
				else:
					self.simulators = ios["simulators"]

		else:
			if "iosKeychains" in info:
				self.keychainNames = info["iosKeychains"]
			if "keychains" in info:
				self.keychains = info["keychains"]
			if "iosCerts" in info:
				for target, c in list(info["iosCerts"].items()):
					if target == "wwdr" or (target == "devNames" and self.target != "device") or (target == "distNames" and self.target == "device"):
						continue
					l = []
					for cert in c:
						l.append(cert)
					self.certs = l
			if "iOSProvisioningProfiles" in info:
				for target, p in list(info["iOSProvisioningProfiles"].items()):
					# TODO: figure out what to do with enterprise profiles
					if (target == "development" and self.target == "device") or (target == "distribution" and self.target == "dist-appstore") or (target == "adhoc" and self.target == "dist-adhoc"):
						l = []
						for profile in p:
							l.append([profile['name'], profile['uuid']])
						self.profiles = l
			self.simulators = None
