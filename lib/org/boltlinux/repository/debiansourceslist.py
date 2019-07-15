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

from org.boltlinux.package.appconfig  import AppConfig
from org.boltlinux.repository.basepackageslist import BasePackagesListMixin

class DebianSourcesList(BasePackagesListMixin):

    def __init__(self, release="stable", component="main", mirror=None,
            cache_dir=None, is_security=False):
        self._release     = release
        self._component   = component
        self._is_security = is_security

        if mirror is not None:
            self._mirror = mirror
        else:
            self._mirror = \
                "http://security.debian.org/debian-security/" if is_security \
                    else "http://ftp.debian.org/debian/"
        #end if

        self._cache_dir = cache_dir or os.path.realpath(
            os.path.join(
                AppConfig.get_config_folder(),
                "cache", "upstream"
            )
        )

        self._target_dir = os.path.join(self._cache_dir, "security" if
                self._is_security else "archive", self._component)
    #end function

    @property
    def filename_gzipped(self):
        return os.path.join(self._target_dir, "Sources.gz")

    @property
    def filename_text(self):
        return os.path.join(self._target_dir, "Sources")

    @property
    def url(self):
        path = \
            "/dists/%(release)s/%(subdir)s%(component)s/source/Sources.gz" % {
                "release": self._release,
                "subdir": "updates/" if self._is_security else "",
                "component": self._component
            }

        return self._mirror + path
    #end function

#end class

