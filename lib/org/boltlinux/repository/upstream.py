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
import sys
import hashlib
import urllib.request

from org.boltlinux.package.libarchive import ArchiveFileReader
from org.boltlinux.package.appconfig import AppConfig
from org.boltlinux.package.progressbar import ProgressBar

class UpstreamRepo:

    def __init__(self, config, verbose=True):
        config = config.get("upstream", {})

        self.verbose      = verbose
        self.release      = config.get("release", "stable")
        self.components   = config.get("components", ["main"])
        self.mirror       = config.get("mirror",
                "http://ftp.debian.org/debian/").rstrip("/")

        self.cache_dir = config.get("cache-dir",
            os.path.realpath(
                os.path.join(
                    AppConfig.get_config_folder(),
                    "cache", "upstream"
                )
            )
        )
    #end function

    def refresh_sources_lists(self):
        for comp in self.components:
            target_dir = os.path.join(self.cache_dir, comp)

            if not os.path.isdir(target_dir):
                os.makedirs(target_dir)

            source_url = self.mirror + "/dists/" + self.release + "/" + \
                    comp + "/source/Sources.gz"
            target_url = os.path.join(target_dir, "Sources.gz")

            try:
                if not self.__check_if_up2date(source_url, target_url):
                    self.__download_sources_gz(source_url, target_url)
            except urllib.error.URLError as e:
                sys.stderr.write("Failed to retrieve '%s': %s\n" % 
                        (source_url, e.reason))
                continue
            #end try

            self.__unpack_sources_gz(target_url)
        #end for
    #end function

    # PRIVATE

    def __check_if_up2date(self, source_url, target_url):
        m = hashlib.sha256()

        try:
            with open(target_url, "rb") as infile:
                while True:
                    buf = infile.read(8*1024)
                    if not buf:
                        break

                    m.update(buf)
                #end while
            #end with
        except FileNotFoundError as e:
            return False

        sha267sum = m.hexdigest()
        request   = urllib.request.Request(source_url, method="HEAD")

        with urllib.request.urlopen(request) as response:
            if response.status != 200:
                return False

        return True
    #end function

    def __download_sources_gz(self, source_url, target_url):
        sys.stdout.write("Retrieving '%s' ...\n" % source_url)

        with urllib.request.urlopen(source_url) as response:
            if response.length:
                progress_bar = ProgressBar(response.length)
            else:
                progress_bar = None
            #end if

            bytes_read = 0
            if self.verbose and progress_bar:
                progress_bar(bytes_read)

            with open(target_url, "wb+") as outfile:
                while True:
                    buf = response.read(8*1024)
                    if not buf:
                        break

                    bytes_read += len(buf)
                    outfile.write(buf)

                    if self.verbose and progress_bar:
                        progress_bar(bytes_read)
                #end while
            #end with
        #end with
    #end function

    def __unpack_sources_gz(self, full_path):
        unzipped_name = full_path[:-3]

        with open(unzipped_name, "wb+") as f:
            with ArchiveFileReader(full_path, raw=True) as archive:
                for entry in archive:
                    while True:
                        buf = archive.read_data(1024)
                        if not buf:
                            break
                        f.write(buf)
                    #end while
                #end for
            #end with
        #end with

        return unzipped_name
    #end function

#end class

