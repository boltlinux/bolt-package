# -*- encoding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2016 Tobias Koch <tobias.koch@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import os
import pwd
import copy
import json
import base64
import socket
import getpass

class AppConfig:

    DEFAULT_CONFIG = """\
{
  "release": {
    "id": "zeus",
    "upstream": "stretch"
  },

  "repositories": [
    { 
      "name": "bolt-os",
      "repo-url": "http://packages.boltlinux.org/repo",
      "rules": "https://github.com/boltlinux/bolt-pkg-rules.git"
    }
  ],

  "upstream": {
    "mirror": "http://ftp.debian.org/debian/",
    "components": [
      "main",
      "contrib",
      "non-free"
    ],
    "refresh-interval": 3600
  },

  "apps": {
    "repository": {
      "appconfig": {
        "DEBUG": false,
        "APPLICATION_ROOT": null,
        "JSON_AS_ASCII": false
      }
    }
  }
}
"""

    INSTANCE = None

    @classmethod
    def instance(klass):
        if not AppConfig.INSTANCE:
            AppConfig.INSTANCE = AppConfig()
        return AppConfig.INSTANCE
    #end function

    @classmethod
    def get_config_folder(klass):
        return os.path.join(os.path.expanduser("~"), ".bolt")

    def load_user_config(self):
        config = None

        user_config_file = os.path.join(
                AppConfig.get_config_folder(), "config.json")

        if os.path.exists(user_config_file):
            with open(user_config_file, "r", encoding="utf-8") as fp:
                config = json.load(fp)
        else:
            config = self.create_default_user_config()

        return config
    #end function

    def create_default_user_config(self):
        user_config_dir  = AppConfig.get_config_folder()
        user_config_file = os.path.join(
              AppConfig.get_config_folder(), "config.json")

        default_config = json.loads(AppConfig.DEFAULT_CONFIG)

        # construct maintainer info
        hostname = socket.gethostname()
        useruid  = os.getuid()
        username = pwd.getpwuid(useruid).pw_name
        realname = pwd.getpwuid(useruid).pw_gecos.split(',')[0]
        usermail = username + "@" + hostname

        default_config["maintainer-info"] = {
            "name":  realname,
            "email": usermail
        }

        for app in default_config.get("apps", {}).values():
            secret_key = base64.encodestring(os.urandom(32)).decode("utf-8")
            app\
                .setdefault("appconfig", {})\
                .setdefault("SECRET_KEY", secret_key)
        #end for

        if not os.path.exists(user_config_dir):
            os.mkdir(user_config_dir, 0o0700)

        with open(user_config_file, "w", encoding="utf-8") as fp:
            fp.write(json.dumps(default_config, indent=4))

        return default_config
    #end function

#end class

