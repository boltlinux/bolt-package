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
import string
import random
import hashlib
import urllib.request

from org.boltlinux.package.libarchive import ArchiveFileReader, ArchiveError
from org.boltlinux.error import RepositoryError

class BasePackagesListMixin:

    def is_up2date(self):
        if not os.path.exists(self.filename_gzipped):
            return False

        old_etag = os.path.basename(os.readlink(self.filename_gzipped))
        try:
            request = urllib.request.Request(self.url, method="HEAD")
            with urllib.request.urlopen(request, timeout=30) as response:
                new_etag = self._etag_from_http_response(response)
        except urllib.error.URLError:
            return False

        return old_etag == new_etag
    #end function

    def refresh(self):
        self.download()
        self.unpack()
    #end function

    def download(self, remove_old=True):
        target_dir = os.path.dirname(self.filename_gzipped)

        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)

        filename_etag = None

        try:
            with urllib.request.urlopen(self.url, timeout=30) as response:
                etag = self._etag_from_http_response(response)

                filename_etag = os.path.join(
                    os.path.dirname(self.filename_gzipped),
                    etag
                )

                with open(filename_etag, "wb+") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        f.write(chunk)

                if remove_old and os.path.lexists(self.filename_gzipped):
                    if os.path.exists(self.filename_gzipped):
                        filename_etag_old = os.path.join(
                            os.path.dirname(self.filename_gzipped),
                            os.readlink(self.filename_gzipped)
                        )
                        os.unlink(filename_etag_old)
                    #end if

                    os.unlink(self.filename_gzipped)
                #end if

                if os.path.exists(filename_etag):
                    os.symlink(etag, self.filename_gzipped)
            #end with
        except (OSError, urllib.error.URLError) as e:
            if filename_etag and os.path.exists(filename_etag):
                os.unlink(filename_etag)
            raise RepositoryError("failed to download '%s': %s" %
                    (self.url, str(e)))
        #end try
    #end function

    def unpack(self):
        try:
            with open(self.filename_text, "wb+") as f:
                with ArchiveFileReader(self.filename_gzipped, raw=True) \
                        as archive:
                    for entry in archive:
                        for chunk in \
                                iter(lambda: archive.read_data(8192), b""):
                            f.write(chunk)
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

            if pkg_info:
                yield pkg_info
        #end for
    #end function

    # SEMI PRIVATE

    def _etag_from_http_response(self, response):
        alphabet = \
            string.ascii_uppercase + \
            string.ascii_lowercase + \
            string.digits

        identifier1 = response.getheader("ETag", "")
        identifier2 = response.getheader("Last-Modified",
            "".join(random.choices(alphabet, k=16)))

        sha256 = hashlib.sha256()
        sha256.update(identifier1.encode("utf-8"))
        sha256.update(identifier2.encode("utf-8"))

        return sha256.hexdigest()[:16]
    #end function

#end class
