import sublime
import sublime_plugin
import os
import shutil
import plistlib
import re

def get_settings():
    settings = sublime.load_settings(__name__ + '.sublime-settings')
    return settings


def get_setting(key, default=None, view=None):
    try:
        if view == None:
            view = sublime.active_window().active_view()
        s = view.settings()
        if s.has("maketi_%s" % key):
            return s.get("maketi_%s" % key)
    except:
        pass
    return get_settings().get(key, default)


class MakeTiCommand(sublime_plugin.WindowCommand):
    mode_list = ["clean", "run", "deploy"]
    deploy_list = ["device", "local", "testflight", "hockey", 'store']
    platform_list = ["ios", "ipad", "iphone", "android", "web"]

    mode = ''
    deploy = ''
    platform = ''
    notes = ''

    def run(self, *args, **kwargs):
        print args, kwargs
        self.window.show_quick_panel(self.mode_list, self._mode_list_callback)

    def plistStringFromProvFile(self, path):
        beginToken = '<?xml'
        endToken = '</plist>'
        f = open(path)
        data = f.read()
        f.close()
        begin = data.index(beginToken)
        end = data.rindex(endToken) + len(endToken) 
        return data[begin:end]

    def getUUIDAndName(self, certPath):
        
        plistString = self.plistStringFromProvFile(certPath)
        plist = plistlib.readPlistFromString(plistString)
        # print plistimport re
        return [plist['UUID'],plist['TeamName']]

    def copyProvisioningProfile(self, certPath, certName):
        dest = os.path.join(os.path.expanduser('~/Library/MobileDevice/Provisioning Profiles'), certName + '.mobileprovision')
        if (not os.path.isfile(dest)):
            print "copying " + certPath + " to " +  dest
            shutil.copyfile(certPath, dest)

    def cleanTarget(self):
        root = self.window.folders()[0]
        buildPath = os.path.join(root, "build")
        iphonePath = os.path.join(buildPath, "iphone")
        androidPath = os.path.join(buildPath, "android")
        shutil.rmtree(iphonePath, True);
        os.makedirs(iphonePath)
        print "cleaned ", iphonePath
        shutil.rmtree(androidPath, True);
        os.makedirs(androidPath)
        print "cleaned ", androidPath

    def updateIOsBuildInTiApp(self):
        #update build number
        root = self.window.folders()[0]
        tiappPath = os.path.join(root, "tiapp.xml")
        if (os.path.isfile(tiappPath)):
            f2 = open(tiappPath, "r")
            tiapp = f2.read()
            f2.close()
            print tiapp
            m = re.search('(?<=<key>CFBundleVersion<\/key>)(\s*<string>)([\d]*)(?=<\/string>)',tiapp)
            if (m != None):
                version = int(m.group(2)) + 1
                print 'updating tiapp CFBundleVersion to ' + version
                tiapp = re.sub('<key>CFBundleVersion</key>\s*<string>[\d]*</string>', '<key>CFBundleVersion</key><string>' + str(version) + '</string>',tiapp)
                f2 = open(tiappPath, "w")
                f2.write(tiapp)
                f2.close()
        else:
            print "tiapp.xml doesnt exist: " + tiappPath

    def updateAndroidBuildInTiApp(self):
        #update build number
        root = self.window.folders()[0]
        tiappPath = os.path.join(root, "tiapp.xml")
        if (os.path.isfile(tiappPath)):
            f2 = open(tiappPath, "r")
            tiapp = f2.read()
            f2.close()
            print tiapp
            m = re.search('(?<=android:versionCode=")([\d]*)(?=")',tiapp)
            if (m != None):
                version = int(m.group(1)) + 1
                print 'updating tiapp android:versionCode to ' + version
                tiapp = re.sub('(?<=android:versionCode=")[\d]*(?=")', str(version),tiapp)
                f2 = open(tiappPath, "w")
                f2.write(tiapp)
                f2.close()
        else:
            print "tiapp.xml doesnt exist: " + tiappPath

    def getCLIParamsForAndroid(self):
        root = self.window.folders()[0]
        env = {}
        env['ANDROID_SDK'] = get_setting('androidsdk', '$ANDROID_SDK')
        parameters = ['--platform', 'android', '--android-sdk', env['ANDROID_SDK']]
        if (self.deploy != 'device'):
            parameters.append('--build-only')
        return [parameters, env]

    def getCLIParamsForIOs(self):
        root = self.window.folders()[0]
        env = {}
        parameters = ['--platform', 'iphone']

        if (self.platform == 'ios'):
            self.platform = 'universal'
        parameters.extend(['--device-family', self.platform])
        parameters.extend(['--deploy-type', 'development'])


        if (self.deploy == 'run'):
            parameters.extend(['--deploy-type', 'test'])
            parameters.extend(['--target', 'simulator'])
        else:
            parameters.extend(['--deploy-type', 'test'])
            certsPath = os.path.join(root, "certs")
            if (self.deploy == 'device'):
                certPath = os.path.join(certsPath, "development.mobileprovision")
            elif (self.deploy == 'store'):
                certPath = os.path.join(certsPath, "appstore.mobileprovision")
            else:
                certPath = os.path.join(certsPath, "distribution.mobileprovision")
            uuidname = self.getUUIDAndName(certPath)
            print uuidname
            self.copyProvisioningProfile(certPath, uuidname[0])

            parameters.extend(['--pp-uuid', uuidname[0]])
            if (self.deploy == 'device'):
                parameters.extend(['--target', 'device'])
                parameters.extend(['--developer-name', uuidname[1]])
            else:
                parameters.extend(['--distribution-name', uuidname[1]])
                if (self.deploy == 'store'):
                    parameters.extend(['--target', 'dist-appstore'])
                elif (self.deploy == 'local'):
                    parameters.extend(['--target', 'dist-adhoc'])
        
        return [parameters, env]

    def launchTiCLI(self):
        root = self.window.folders()[0]
        parameters = ["/usr/local/bin/node", "/usr/local/bin/titanium", "build", '--no-colors', '--force', '--project-dir', root, '--log-level', 'trace']
        if (self.deploy == 'local'):
            parameters.extend(['--output-dir', root])

        platRes = [[],{}]
        if (self.platform == 'ipad' or self.platform == 'iphone' or self.platform == 'ios'):
            platRes = self.getCLIParamsForIOs()
            if (self.deploy == 'local'):
                self.updateIOsBuildInTiApp();
        elif (self.platform == 'android'):
            platRes = self.getCLIParamsForAndroid()
            if (self.deploy == 'local'):
                self.updateAndroidBuildInTiApp();
        parameters.extend(platRes[0])
        print parameters
        self.window.run_command("exec", {"cmd": parameters, "env": platRes[1]})

    def launchMake(self):
        sublime.log_commands(True)
        sublime.log_input(True)
        sublime.active_window().run_command("show_panel", {"panel": "console", "toggle": True})
        if (self.mode == 'clean'):
            self.cleanTarget()
        else:
            self.launchTiCLI()
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

        if (self.deploy != '' and self.deploy != 'device'):
            if (self.deploy == 'local'):
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
                    self.window.show_quick_panel(self.platform_list, self._platform_list_callback)
                else:
                    if(self.mode == 'deploy'):
                        self.window.show_quick_panel(self.deploy_list, self._deploy_list_callback)

    def _deploy_list_callback(self, index):
        if (index > -1):
            self.deploy = self.deploy_list[index]
            self.window.show_quick_panel(self.platform_list, self._platform_list_callback)

    def _platform_list_callback(self, index):
        # root = self.window.folders()[0]
        if (index > -1):
            self.platform = self.platform_list[index]
            if (self.mode == 'deploy' and self.deploy != 'device' and self.deploy != 'local' and self.deploy != 'store'):
                self.window.show_input_panel("Release Notes", "", self._release_note_on_done, 0, 0)
            else:
                self.launchMake()

    def _release_note_on_done(self, entry):
        if (entry != ''):
            self.notes = entry
            self.launchMake()
        else:
            sublime.error_message("It s not safe to release without a changelog, aborting!")

    # def _release_note_on_change(self, entry):
             # sublime.error_message("dont know the meaning ...!")
    # def _release_note_on_cancel(self):
             # sublime.error_message("operation cancelled!")
