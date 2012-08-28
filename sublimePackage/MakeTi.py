import sublime
import sublime_plugin


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
    deploy_list = ["device", "local", "testflight", "hockey"]
    platform_list = ["ios", "ipad", "iphone", "android", "web"]

    mode = ''
    deploy = ''
    platform = ''
    notes = ''

    def run(self, *args, **kwargs):
        print args, kwargs
        self.window.show_quick_panel(self.mode_list, self._mode_list_callback)

    def launchMake(self):
        sublime.log_commands(True)
        sublime.log_input(True)
        sublime.active_window().run_command("show_panel", {"panel": "console", "toggle": True})
        root = self.window.folders()[0]
        parameters = ["make", "-C", root, self.mode, "platform=" + self.platform, "android_sdk_path=" + get_setting('androidsdk'), 'apkonly=true']
        if (self.deploy != '' and self.deploy != 'device'):
            if (self.deploy == 'local'):
                parameters.append("dir=" + str(get_setting('local_deploy_dir', root)))
            else:
                parameters.append(self.deploy + "=true")
        if (self.notes != ''):
            parameters.append("notes=\"" + self.notes + "\"")
        if (self.platform == 'ipad' or self.platform == 'iphone' or self.platform == 'ios'):
            parameters.append("cert_dist=" + str(get_setting('cert_dist_identity', 10)))
            # if (self.deploy == 'device'):
            #     parameters.append("cert_dev=" + str(s.get('cert_dev_identity', 0)))
            # else:
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
            if (self.mode == 'deploy' and self.deploy != 'device' and self.deploy != 'local'):
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
