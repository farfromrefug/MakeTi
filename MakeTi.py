import sublime
import sublime_plugin
import os
import shutil
import plistlib
import re

PLUGIN_FOLDER = os.path.dirname(os.path.realpath(__file__))
SETTINGS_FILE = __name__ + ".sublime-settings"

settings = sublime.load_settings(SETTINGS_FILE)

def get_setting(key, default=None, view=None):
    try:
        if view == None:
            view = sublime.active_window().active_view()
        s = view.settings()
        if s.has("maketi_%s" % key):
            return s.get("maketi_%s" % key)
    except:
        pass
    if settings.has("maketi_%s" % key):
        return settings.get(key, default)
    else:
        return default


class MakeTiCommand(sublime_plugin.WindowCommand):
    mode_list = ["clean", "run", "deploy"]
    run_list = ["device", "emulator"]
    deploy_list = ["adhoc", "debug", "testflight", "hockey", 'store']
    platform_list = ["ios", "ipad", "iphone", "android", "web"]
    print ('creating MakeTiCommand')
    lastcommand = [];
    lastplatres = [[],{}];

    mode = ''
    run_mode = ''
    deploy = ''
    platform = ''
    notes = ''

    def run(self, **kwargs):
        print (str(kwargs))
        if ('runLastCommand' in kwargs and kwargs['runLastCommand'] == True):
            self.runLastCommand()
        else:
            self.mode = ''
            self.run_mode = 'device'
            self.deploy = ''
            self.platform = ''
            self.notes = ''
            self.show_quick_panel(self.mode_list, self._mode_list_callback)

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
        plist = plistlib.readPlistFromBytes(bytes(plistString, 'UTF-8'))
        print (plist)
        return [plist['UUID'],plist['TeamName'], plist['TeamIdentifier'][0]]

    def copyProvisioningProfile(self, certPath, certName):
        dest = os.path.join(os.path.expanduser('~/Library/MobileDevice/Provisioning Profiles'), certName + '.mobileprovision')
        if (not os.path.isfile(dest)):
            print ("copying " + certPath + " to " +  dest)
            shutil.copyfile(certPath, dest)

    def cleanTarget(self):
        root = self.window.folders()[0]
        buildPath = os.path.join(root, "build")
        iphonePath = os.path.join(buildPath, "iphone")
        androidPath = os.path.join(buildPath, "android")
        shutil.rmtree(iphonePath, True);
        os.makedirs(iphonePath)
        print ("cleaned ", iphonePath)
        shutil.rmtree(androidPath, True);
        os.makedirs(androidPath)
        print ("cleaned ", androidPath)

    def updateIOsBuildInTiApp(self):
        #update build number
        root = self.window.folders()[0]
        tiappPath = os.path.join(root, "tiapp.xml")
        if (os.path.isfile(tiappPath)):
            f2 = open(tiappPath, "r")
            tiapp = f2.read()
            f2.close()
            m = re.search('(?<=<key>CFBundleVersion<\/key>)(\s*<string>)([\d]*)(?=<\/string>)',tiapp)
            if (m != None):
                version = int(m.group(2)) + 1
                print ('updating tiapp CFBundleVersion to ' + str(version))
                tiapp = re.sub('<key>CFBundleVersion</key>\s*<string>[\d]*</string>', '<key>CFBundleVersion</key><string>' + str(version) + '</string>',tiapp)
                f2 = open(tiappPath, "w")
                f2.write(tiapp)
                f2.close()
        else:
            print ("tiapp.xml doesnt exist: " + tiappPath)

    def getSdkVersion(self):
        #update build number
        root = self.window.folders()[0]
        tiappPath = os.path.join(root, "tiapp.xml")
        if (os.path.isfile(tiappPath)):
            f2 = open(tiappPath, "r")
            tiapp = f2.read()
            f2.close()
            m = re.search('(?<=<sdk-version>)(.*)([\d]*)(?=<\/sdk-version>)',tiapp)
            if (m != None):
                return m.group(1)
            else:
                return None
        else:
            return None

    def updateAndroidBuildInTiApp(self):
        #update build number
        root = self.window.folders()[0]
        tiappPath = os.path.join(root, "tiapp.xml")
        if (os.path.isfile(tiappPath)):
            f2 = open(tiappPath, "r")
            tiapp = f2.read()
            f2.close()
            m = re.search('(?<=android:versionCode=")([\d]*)(?=")',tiapp)
            if (m != None):
                version = int(m.group(1)) + 1
                print ('updating tiapp android:versionCode to ' + str(version))
                tiapp = re.sub('(?<=android:versionCode=")[\d]*(?=")', str(version),tiapp)
                f2 = open(tiappPath, "w")
                f2.write(tiapp)
                f2.close()
        else:
            print ("tiapp.xml doesnt exist: " + tiappPath)

    def getCLIParamsForAndroid(self):
        root = self.window.folders()[0]
        env = {}
        env['ANDROID_SDK'] = get_setting('androidsdk', os.getenv('ANDROID_SDK', '/Volumes/data/dev/androidSDK'))
        parameters = ['--platform', 'android', '--android-sdk', env['ANDROID_SDK']]

        keystore = get_setting('android_keystore', "")
        if (keystore != "" and self.deploy == 'store'):
            parameters.extend(['--target', 'dist-playstore'])
            parameters.extend(['--keystore', os.path.join(root, keystore) ])
            parameters.extend(['--password', get_setting('android_keystore_pass', "") ])
            parameters.extend(['--alias', get_setting('android_keystore_alias', "") ])
        else:
            if (self.run_mode == 'device'):
                parameters.extend(['--target', 'device'])
            if (self.deploy == 'adhoc'):
                parameters.append('--build-only')
                parameters.extend(['--deploy-type', get_setting('adhoc_deploytype', 'test')])
            elif (self.deploy == 'debug'):
                parameters.extend(['--deploy-type', 'development'])
        return [parameters, env]

    def getCLIParamsForIOs(self):
        root = self.window.folders()[0]
        env = {}
        parameters = ['--platform', 'iphone']

        if (self.platform == 'ios'):
            self.platform = 'universal'
        parameters.extend(['--device-family', self.platform])


        if (self.run_mode == 'emulator'):
            parameters.extend(['--target', 'simulator'])
            # parameters.extend(['-device-id', '"' + str(get_setting('ios_device_id', 3)) + '"'])
            parameters.extend(['--deploy-type', 'development'])
        else:
            parameters.extend(['--deploy-type', 'test'])
            certsPath = os.path.join(root, "certs")
            if (self.deploy == 'debug'):
                certPath = os.path.join(certsPath, "development.mobileprovision")
            elif (self.deploy == 'store'):
                certPath = os.path.join(certsPath, "appstore.mobileprovision")
            else:
                certPath = os.path.join(certsPath, "distribution.mobileprovision")
            uuidname = self.getUUIDAndName(certPath)
            print (uuidname)
            self.copyProvisioningProfile(certPath, uuidname[0])

            if (get_setting('ios_sdk') != None):
                parameters.extend(["--ios-version", str(get_setting('ios_sdk', '5.0'))])

            parameters.extend(['--pp-uuid', uuidname[0]])
            if (self.deploy == 'debug'):
                parameters.append('--build-only')
                parameters.extend(['--target', 'device'])
                parameters.extend(['--deploy-type', 'development'])
                parameters.extend(['--developer-name', get_setting('dev_name', 'Martin Guillon')])
            else:
                # parameters.extend(['--distribution-name', uuidname[1]])
                parameters.extend(['--distribution-name', uuidname[1] + " (" + uuidname[2] + ")"])
                if (self.deploy == 'store'):
                    parameters.extend(['--target', 'dist-appstore'])
                elif (self.deploy == 'adhoc'):
                    parameters.extend(['--deploy-type', get_setting('adhoc_deploytype', 'test')])
                    parameters.extend(['--target', 'dist-adhoc'])
        
        return [parameters, env]

    def runLastCommand(self):
        self.window.run_command("exec", {"cmd": self.lastcommand, "env": self.lastplatres[1]})

    def launchTiCLI(self):
        root = self.window.folders()[0]
        parameters = ["/usr/local/bin/node", "/usr/local/bin/titanium", "build", '--no-colors', '--project-dir', root, '--log-level', 'trace']
        # if (self.deploy == 'local' or self.deploy == 'store'):
        parameters.extend(['--output-dir', root])

        sdk=self.getSdkVersion()
        if (sdk != None):
            parameters.extend(['--sdk', sdk])

        platRes = [[],{}]
        if (self.platform == 'ipad' or self.platform == 'iphone' or self.platform == 'ios'):
            platRes = self.getCLIParamsForIOs()
            if (self.deploy == 'adhoc'):
                self.updateIOsBuildInTiApp();
        elif (self.platform == 'android'):
            platRes = self.getCLIParamsForAndroid()
            if (self.deploy == 'adhoc'):
                self.updateAndroidBuildInTiApp();
        parameters.extend(platRes[0])
        print (' '.join(parameters))
        self.lastcommand = parameters;
        self.lastplatres = platRes;
        # self.window.run_command("exec", {"cmd": 'export', "shell":True})
        # try:
        self.window.run_command("exec", {"cmd": parameters, "env": platRes[1]})
        # except:
        #     self.showNotification('Build ERROR', 'Could not build ' + root)
        # else:
        # self.showNotification('Build Success', 'built ' + root)
        # finally:
        #     sublime.active_window().run_command("show_panel", {"panel": "console", "toggle": True})

    def showNotification(self, _title, _msg):
        sublime.log_commands(False)
        sublime.log_input(False)
        self.window.run_command("exec", {"cmd": ["terminal-notifier", "-message", _msg, '-title', _title, '-activate', 'com.sublimetext.2']})
        sublime.log_commands(True)
        sublime.log_input(True)

    def launchMake(self):
        sublime.log_commands(True)
        sublime.log_input(True)
        sublime.active_window().run_command("show_panel", {"panel": "console", "toggle": True})
        if (self.mode == 'clean'):
            self.cleanTarget()
        else:
            sublime.set_timeout_async(self.launchTiCLI, 0)
            # self.runShellCommand()

    def runShellCommand(self):
        root = self.window.folders()[0]
        buildPath = os.path.join(root, "build")
        plateform = 'android'
        if (self.platform == 'ipad' or self.platform == 'iphone' or self.platform == 'ios'):
            plateform = 'iphone'
        plateformBuildPath = os.path.join(buildPath, plateform)
        if not os.path.exists(plateformBuildPath):
            os.makedirs(plateformBuildPath)

        parameters = [os.path.join(root, "maketi", "titanium.sh")]
        parameters.append("DEVICE_TYPE=" + self.platform)
        parameters.append("PROJECT_ROOT=\"" + root + "\"")
        if(self.mode == 'deploy'):
            parameters.append("BUILD_TYPE='device'")

        if (plateform == 'android'):
            parameters.append("android_sdk_path=" + get_setting('androidsdk'))
            if (self.deploy == 'local'):
                parameters.append('APK_ONLY=true')

        elif (plateform == 'iphone'):
            if (self.deploy == 'device'):
                parameters.append("cert_dev=" + str(get_setting('cert_dev_identity', 0)))
            else:
                parameters.append("cert_dist=" + str(get_setting('cert_dist_identity', 10)))
            if (get_setting('ios_sdk') != None):
                parameters.append("IOS_SDK=" + str(get_setting('ios_sdk')))

        if (self.deploy != '' and self.deploy != 'debug'):
            if (self.deploy == 'adhoc'):
                parameters.append("dir=\"" + str(get_setting('local_deploy_dir', root)) + "\"")
            else:
                parameters.append(self.deploy + "=true")
        if (self.notes != ''):
            parameters.append("notes=\"" + self.notes + "\"")
        self.window.run_command("exec", {"cmd": parameters})

    def _mode_list_callback(self, index):
        if (index > -1):
            self.mode = self.mode_list[index]
            if (self.mode_list[index] == 'clean'):
                self.launchMake()
            else:
                if (self.mode == 'run'):
                    self.show_quick_panel(self.run_list, self._run_list_callback)
                else:
                    if(self.mode == 'deploy'):
                        self.run_mode = 'device'
                        self.show_quick_panel(self.deploy_list, self._deploy_list_callback)

    def _deploy_list_callback(self, index):
        if (index > -1):
            self.deploy = self.deploy_list[index]
            self.show_quick_panel(self.platform_list, self._platform_list_callback)

    def _run_list_callback(self, index):
        if (index > -1):
            self.run_mode = self.run_list[index]
            self.show_quick_panel(self.platform_list, self._platform_list_callback)

    def _platform_list_callback(self, index):
        # root = self.window.folders()[0]
        if (index > -1):
            self.platform = self.platform_list[index]
            if (self.mode == 'deploy' and self.deploy != 'store' and self.deploy != 'adhoc'):
                self.window.show_input_panel("Release Notes", "", self._release_note_on_done, 0, 0)
            else:
                self.launchMake()

    def _release_note_on_done(self, entry):
        if (entry != ''):
            self.notes = entry
            self.launchMake()
        else:
            sublime.error_message("It s not safe to release without a changelog, aborting!")

    def show_quick_panel(self, options, done):
        sublime.set_timeout(lambda: self.window.show_quick_panel(options, done), 5)
    # def _release_note_on_change(self, entry):
             # sublime.error_message("dont know the meaning ...!")
    # def _release_note_on_cancel(self):
             # sublime.error_message("operation cancelled!")
