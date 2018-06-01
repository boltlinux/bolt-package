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
import sys
import hashlib
import urllib.request

from org.boltlinux.package.libarchive import ArchiveFileReader
from org.boltlinux.package.appconfig import AppConfig
from org.boltlinux.package.progressbar import ProgressBar
from org.boltlinux.package.xpkg import BaseXpkg
from org.boltlinux.repository.flaskapp import app, db
from org.boltlinux.repository.models import SourcePackage

class UpstreamRepo:

    def __init__(self, config, verbose=True):
        self.release = config.get("release", {}).get("upstream", "stable")

        config = config.get("upstream", {})

        self.verbose    = verbose
        self.components = config.get("components", ["main"])
        self.mirror     = config.get("mirror",
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
        requires_update = []

        for comp in self.components:
            target_dir = os.path.join(self.cache_dir, comp)

            if not os.path.isdir(target_dir):
                os.makedirs(target_dir)

            target_url = os.path.join(target_dir, "Sources.gz")

            try:
                if not self.__check_if_up2date(comp, target_url):
                    self.__download_sources_gz(comp, target_url)
                    requires_update.append(comp)
                #end if
            except urllib.error.URLError as e:
                sys.stderr.write("Failed to retrieve '%s' sources: %s\n" %
                        (comp, e.reason))
                continue
            #end try

            self.__unpack_sources_gz(target_url)
        #end for

        return requires_update
    #end function

    def update_repository_db(self, components):
        pkg_index = {}

        for comp in components:
            sources_file = os.path.join(self.cache_dir, comp, "Sources")
            self.__parse_sources_file(sources_file, pkg_index)
        #end for

        with app.app_context():
            for entry in SourcePackage.query.all():
                pkg_name = entry.name

                if pkg_name in pkg_index:
                    old_version = entry.upstream_version
                    new_version = pkg_index[pkg_name].get("Version")

                    if old_version is None or BaseXpkg.compare_versions(
                            new_version, old_version) > 0:
                        entry.upstream_version = new_version
                    #end if
            #end for

            db.session.commit();
        #end with
    #end function

    # PRIVATE

    def __parse_sources_file(self, filename, pkg_index):
        if not os.path.isfile(filename):
            return pkg_index

        pkg_info  = {}

        with open(filename, "r", encoding="utf-8") as f:
            key = None

            for line in f:
                line = line.rstrip()

                if not line:
                    if pkg_info:
                        try:
                            pkg_name = pkg_info["Package"]

                            if not pkg_name in pkg_index:
                                pkg_index[pkg_name] = pkg_info
                            else:
                                old_version = pkg_index[pkg_name]["Version"]
                                new_version = pkg_info["Version"]

                                if BaseXpkg.compare_versions(new_version,
                                        old_version) > 0:
                                    pkg_index[pkg_name] = pkg_info
                            #end if
                        except KeyError:
                            pass
                        pkg_info = {}
                    #end if

                    continue
                #end if

                if re.match(r"^\s+", line):
                    if key is not None:
                        pkg_info[last_item] += " " + line.lstrip()
                else:
                    key, value = line.split(":", 1)

                    if key in ["Package", "Version"]:
                        pkg_info[key] = value.lstrip()
                    else:
                        key = None
                #end if
            #end for
        #end with

        return pkg_index
    #end function

    def __check_if_up2date(self, component, target_url):
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

        source_url = self.mirror + "/dists/" + self.release + "/" + \
                component + "/source/by-hash/SHA256/" + m.hexdigest()
        request = urllib.request.Request(source_url, method="HEAD")

        try:
            with urllib.request.urlopen(request) as response:
                if response.status != 200:
                    return False
        except urllib.error.HTTPError as e:
            return False

        return True
    #end function

    def __download_sources_gz(self, component, target_url):
        source_url = self.mirror + "/dists/" + self.release + "/" + \
                component + "/source/Sources.gz"

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
                        buf = archive.read_data(8*1024)
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

