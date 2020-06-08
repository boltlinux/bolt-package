# -*- encoding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2016-2018 Tobias Koch <tobias.koch@gmail.com>
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
    "general": {
        "default-release": "devel"
    },

    "maintainer-info": {
        "email": "max.mustermann@example.com",
        "name": "Max Mustermann"
    },

    "releases": [
        {
            "id": "devel",
            "version_id": "00.00",
            "upstream": {
                "id": "stable",
                "components": [
                    "main",
                    "contrib",
                    "non-free"
                ],
                "mirror": "http://ftp.debian.org/debian/",
                "refresh-interval": 3600
            },
            "supported-architectures": {
                "musl": [
                    "aarch64",
                    "armv6",
                    "armv7a",
                    "i686",
                    "mipsel",
                    "mips64el",
                    "powerpc64le",
                    "s390x",
                    "x86_64"
                ]
            },
            "repositories": {
                "core": {
                    "rules": "https://github.com/boltlinux/bolt-pkg-rules.git@master",
                    "repo-url": "http://archive.boltlinux.org/dists"
                }
            }
        }
    ],

    "apps": {
        "repository": {
            "appconfig": {
                "APPLICATION_ROOT": null,
                "DEBUG": false,
                "JSON_AS_ASCII": false
            }
        }
    }
}"""

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

    def __init__(self):
        self.config = self.load_user_config()

    def __getitem__(self, key):
        return self.config[key]

    def get(self, key, default=None):
        return self.config.get(key, default)

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

    def get_default_release(self):
        return self.config\
            .get("general", {})\
            .get("default-release", "devel")
    #end function

    def get_release_config(self, release_name):
        for release in self.config.get("releases", []):
            if release.get("id", "") == release_name:
                return release
        #end for

        return None
    #end function

    def get_cache_dir(self):
        cache_dir = self.config\
            .get("general", {})\
            .get("system", {})\
            .get("cache-dir")

        if not cache_dir:
            cache_dir = os.path.realpath(
                os.path.join(self.get_config_folder(), "cache")
            )
        #end if

        return cache_dir
    #end function

#end class
