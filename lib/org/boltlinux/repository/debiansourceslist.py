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
from org.boltlinux.package.libarchive import ArchiveFileReader, ArchiveError
from org.boltlinux.repository.basepackageslist import BasePackagesListMixin
from org.boltlinux.error import RepositoryError

class DebianSourcesList(BasePackagesListMixin):

    def __init__(self, release="stable", component="main", mirror=None,
            cache_dir=None):
        self._release   = release
        self._component = component
        self._mirror    = mirror if mirror is not None else \
            "http://ftp.debian.org/debian/"

        self._cache_dir = cache_dir or os.path.realpath(
            os.path.join(
                AppConfig.get_config_folder(),
                "cache", "upstream"
            )
        )

        self._target_dir = os.path.join(self._cache_dir, self._component)
    #end function

    @property
    def filename_gzipped(self):
        return os.path.join(self._target_dir, "Sources.gz")

    @property
    def filename_text(self):
        return os.path.join(self._target_dir, "Sources")

    @property
    def url(self):
        return self._mirror    + "/dists/" + \
               self._release   + "/"       + \
               self._component + "/source/Sources.gz"
    #end function

    @property
    def by_hash_url(self):
        return self._mirror    + "/dists/" + \
               self._release   + "/"       + \
               self._component + "/source/by-hash/"
    #end function

#end class

