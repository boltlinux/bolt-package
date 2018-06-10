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
import logging

from org.boltlinux.package.libarchive import ArchiveFileReader
from org.boltlinux.package.appconfig import AppConfig
from org.boltlinux.package.xpkg import BaseXpkg
from org.boltlinux.repository.flaskapp import app, db
from org.boltlinux.repository.models import UpstreamSource

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

        self.log = logging.getLogger("org.boltlinux.repository")
    #end function

    def refresh_sources_lists(self):
        requires_update = []

        for comp in self.components:
            target_dir = os.path.join(self.cache_dir, comp)
            target_url = os.path.join(target_dir, "Sources.gz")

            if not os.path.isdir(target_dir):
                os.makedirs(target_dir)

            try:
                up_to_date = self.__check_if_up2date(comp, target_url)

                if up_to_date:
                    self.log.info("upstream sources index for component '%s' "
                        "is up to date." % comp)
                else:
                    self.log.info("upstream sources index for component '%s' "
                        "requires update." % comp)

                    self.__download_sources_gz(comp, target_url)
                    self.__unpack_sources_gz(target_url)

                    requires_update.append(comp)
                #end if
            except urllib.error.URLError as e:
                self.log.error("Failed to retrieve '%s' sources: %s" %
                        (comp, e.reason))
                continue
            #end try
        #end for

        return requires_update
    #end function

    def update_repository_db(self):
        pkg_index = {}

        for comp in self.components:
            sources_file = os.path.join(self.cache_dir, comp, "Sources")
            self.__parse_sources_file(sources_file, pkg_index)
        #end for

        with app.app_context():
            stored_pkg_index = dict([(obj.name, obj) for obj in
                    UpstreamSource.query.all()])

            for pkg_name in sorted(pkg_index):
                pkg_info = pkg_index[pkg_name]

                if not pkg_name in stored_pkg_index:
                    source_pkg = UpstreamSource(name=pkg_name,
                            version=pkg_info["Version"])
                    db.session.add(source_pkg)
                    stored_pkg_index[pkg_name] = source_pkg
                else:
                    source_pkg = stored_pkg_index[pkg_name]

                    old_version = source_pkg.version
                    new_version = pkg_info["Version"]

                    if BaseXpkg.compare_versions(new_version, old_version) > 0:
                        source_pkg.version = new_version
                #end if
            #end for

            db.session.commit()
        #end with
    #end function

    # PRIVATE

    def __parse_sources_file(self, filename, pkg_index):
        if not os.path.isfile(filename):
            return pkg_index

        with open(filename, "r", encoding="utf-8") as f:
            buf = f.read().strip()

        for pkg_txt in re.split(r"\n\n+", buf):
            pkg_info = {}
            key      = None

            for line in pkg_txt.splitlines():
                if re.match(r"^\s+", line):
                    if key is not None:
                        pkg_info[key] += " " + line.lstrip()
                else:
                    key, value = line.split(":", 1)

                    if key in ["Package", "Version"]:
                        pkg_info[key] = value.lstrip()
                    else:
                        key = None
                #end if
            #end for

            try:
                pkg_name    = pkg_info["Package"]
                new_version = pkg_info["Version"]

                if not pkg_name in pkg_index:
                    pkg_index[pkg_name] = pkg_info
                else:
                    old_version = pkg_index[pkg_name]["Version"]

                    if BaseXpkg.compare_versions(new_version,
                            old_version) > 0:
                        pkg_index[pkg_name] = pkg_info
                #end if
            except KeyError:
                pass
        #end for

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

        self.log.info("Retrieving '%s' ..." % source_url)

        with urllib.request.urlopen(source_url) as response:
            with open(target_url, "wb+") as outfile:
                while True:
                    buf = response.read(8*1024)
                    if not buf:
                        break
                    outfile.write(buf)
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

