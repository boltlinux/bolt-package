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
import re
import hashlib
import urllib.request

from org.boltlinux.package.libarchive import ArchiveFileReader, ArchiveError
from org.boltlinux.error import RepositoryError

class BasePackagesListMixin:

    def is_up2date(self):
        m = hashlib.sha256()

        try:
            with open(self.filename_gzipped, "rb") as infile:
                while True:
                    buf = infile.read(8*1024)
                    if not buf:
                        break
                    m.update(buf)
                #end while
            #end with
        except FileNotFoundError as e:
            return False

        hash_url_sha256 = self.by_hash_url + "/SHA256/" + m.hexdigest()
        request = urllib.request.Request(hash_url_sha256, method="HEAD")

        try:
            with urllib.request.urlopen(request) as response:
                if response.status != 200:
                    return False
        except urllib.error.URLError as e:
            return False

        return True
    #end function

    def refresh(self):
        self.download()
        self.unpack()
    #end function

    def download(self):
        target_dir = os.path.dirname(self.filename_gzipped)

        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)

        try:
            with urllib.request.urlopen(self.url) as response:
                with open(self.filename_gzipped, "wb+") as outfile:
                    while True:
                        buf = response.read(8*1024)
                        if not buf:
                            break
                        outfile.write(buf)
                    #end while
                #end with
            #end with
        except (OSError, urllib.error.URLError) as e:
            raise RepositoryError("failed to download '%s': %s" %
                    (self.url, str(e)))
    #end function

    def unpack(self):
        try:
            with open(self.filename_text, "wb+") as f:
                with ArchiveFileReader(self.filename_gzipped, raw=True) as archive:
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
                    (self.filename_gzipped, str(e)))
        #end try
    #end function

    def __iter__(self):
        if not os.path.isfile(self.filename_text):
            return

        with open(self.filename_text, "r", encoding="utf-8") as f:
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

#end class

