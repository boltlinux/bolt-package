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
import re
import hashlib
import logging
import urllib.request

from org.boltlinux.package.appconfig  import AppConfig
from org.boltlinux.package.libarchive import ArchiveFileReader, ArchiveError
from org.boltlinux.error import RepositoryError

class SourcesList:

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

    def is_up2date(self):
        m = hashlib.sha256()

        try:
            with open(self.sources_gz, "rb") as infile:
                while True:
                    buf = infile.read(8*1024)
                    if not buf:
                        break

                    m.update(buf)
                #end while
            #end with
        except FileNotFoundError as e:
            return False

        hash_url = \
                self._mirror    + "/dists/" + \
                self._release   + "/"       + \
                self._component + "/source/by-hash/SHA256/" \
                    + m.hexdigest()

        request = urllib.request.Request(hash_url, method="HEAD")

        try:
            with urllib.request.urlopen(request) as response:
                if response.status != 200:
                    return False
        except urllib.error.URLError as e:
            return False

        return True
    #end function

    def refresh(self):
        if not os.path.isdir(self._target_dir):
            os.makedirs(self._target_dir)

        if self.is_up2date():
            return

        self.download()
        self.unpack()
    #end function

    def download(self):
        try:
            with urllib.request.urlopen(self.sources_url) as response:
                with open(self.sources_gz, "wb+") as outfile:
                    while True:
                        buf = response.read(8*1024)
                        if not buf:
                            break
                        outfile.write(buf)
                    #end while
                #end with
            #end with
        except urllib.error.URLError as e:
            raise RepositoryError("failed to download '%s': %s" %
                    (self.sources_url, str(e)))
    #end function

    def unpack(self):
        try:
            with open(self.sources_txt, "wb+") as f:
                with ArchiveFileReader(self.sources_gz, raw=True) as archive:
                    for entry in archive:
                        while True:
                            buf = archive.read_data(8*1024)
                            if not buf:
                                break
                            f.write(buf)
                        #end while
                    #end for
                #end with
            #end with
        except (OSError, ArchiveError) as e:
            raise RepositoryError("failed to unpack '%s': %s" %
                    (self.sources_gz, str(e)))
        #end try
    #end function

    def __iter__(self):
        if not os.path.isfile(self.sources_txt):
            return

        with open(self.sources_txt, "r", encoding="utf-8") as f:
            buf = f.read().strip()

        for pkg_txt in re.split(r"\n\n+", buf):
            pkg_info = {}
            key      = None

            for line in pkg_txt.splitlines():
                if re.match(r"^\s+", line):
                    if key is not None:
                        pkg_info[key] += " " + line.lstrip()
                else:
                    key, value    = line.split(":", 1)
                    pkg_info[key] = value.lstrip()
                #end if
            #end for

            yield pkg_info
        #end for
    #end function

    @property
    def sources_gz(self):
        return os.path.join(self._target_dir, "Sources.gz")

    @property
    def sources_txt(self):
        return os.path.join(self._target_dir, "Sources")

    @property
    def sources_url(self):
        return self._mirror    + "/dists/" + \
               self._release   + "/"       + \
               self._component + "/source/Sources.gz"
    #end function

#end class

