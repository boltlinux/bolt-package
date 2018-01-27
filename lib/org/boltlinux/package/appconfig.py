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
import socket
import getpass

class AppConfig:

    DEFAULT_CONFIG = """\
{

  "repositories": [
    {
      "name": "packages.boltlinux.org",
      "url":  "http://packages.boltlinux.org/repo/sources"
    }
  ]
}
"""

    @classmethod
    def get_config_folder(klass):
        return os.path.join(os.path.expanduser("~"), ".bolt")

    @classmethod
    def load_user_config(klass):
        config = json.loads(AppConfig.DEFAULT_CONFIG)

        user_config_file = os.path.join(
                AppConfig.get_config_folder(), "config.json")

        if os.path.exists(user_config_file):
            with open(user_config_file, "r", encoding="utf-8") as fp:
                config = json.load(fp)
            #end with
        else:
            AppConfig.create_default_user_config()
        #end if

        return config
    #end function

    @classmethod
    def create_default_user_config(klass):
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

        if not os.path.exists(user_config_dir):
            os.mkdir(user_config_dir, 0o0700)

        print(default_config)

        with open(user_config_file, "w", encoding="utf-8") as fp:
            fp.write(json.dumps(default_config, indent=4))
    #end function

#end class
