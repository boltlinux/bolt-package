# -*- encoding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2019 Tobias Koch <tobias.koch@gmail.com>
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

import hashlib
import logging
import os
import random
import re
import string
import urllib.error
import urllib.request

from org.boltlinux.error import BoltError
from org.boltlinux.package.libarchive import ArchiveFileReader
from org.boltlinux.deb2bolt.debianpackagemetadata import \
        DebianPackageMetaData, DebianPackageVersion

class DebianPackageCacheError(BoltError):
    pass

class DebianPackageDict(dict):

    def keys(self):
        for version in super().keys():
            yield DebianPackageVersion(version)

    def items(self):
        for version, pkg_obj in super().items():
            yield DebianPackageVersion(version), pkg_obj

    def __iter__(self):
        for version in super().keys():
            yield DebianPackageVersion(version)

#end class

class DebianPackageCache:

    SOURCE = 1
    BINARY = 2

    def __init__(self, release, arch="amd64", pockets=None, cache_dir=None,
            security_enabled=True, updates_enabled=False):
        self.log = logging.getLogger("org.boltlinux.tools")

        self.release = release
        self.arch = arch

        if not pockets:
            pockets = ["main", "contrib", "non-free"]
        self.pockets = pockets

        if not cache_dir:
            cache_dir = os.path.realpath(os.path.join(
                os.getcwd(), "pkg-cache"))

        self._cache_dir = cache_dir

        self.sources_list = [
            (
                "release",
                "http://ftp.debian.org/debian/dists/{}"
                    .format(release)
            )
        ]

        if security_enabled:
            self.sources_list.append(
                (
                    "security",
                    "http://security.debian.org/debian-security/dists/{}/updates"
                        .format(release)
                )
            )
        #end if

        if updates_enabled:
            self.sources_list.append(
                (
                    "updates",
                    "http://ftp.debian.org/debian/dists/{}-updates"
                        .format(release)
                )
            )
        #end if

        self.source = {}
        self.binary = {}
    #end function

    def open(self):
        self._parse_package_list()

    def update(self, what=SOURCE|BINARY):
        pkg_types = []

        if what & self.SOURCE:
            pkg_types.append("source")
        if what & self.BINARY:
            pkg_types.extend(["binary-{}".format(self.arch), "binary-all"])

        for component, base_url in self.sources_list:
            for pocket in self.pockets:
                for type_ in pkg_types:
                    cache_dir = os.path.join(self._cache_dir, self.release,
                            component, pocket, type_)

                    if not os.path.isdir(cache_dir):
                        os.makedirs(cache_dir)

                    if type_ == "source":
                        source = "{}/{}/source/Sources.gz"\
                            .format(base_url, pocket)
                        target = os.path.join(cache_dir, "Sources.gz")
                    else:
                        source = "{}/{}/{}/Packages.gz"\
                            .format(base_url, pocket, type_)
                        target = os.path.join(cache_dir, "Packages.gz")

                    # Download file into symlinked blob.
                    try:
                        # Check if resource has changed.
                        old_etag = self._etag_for_file(target)
                        new_etag = self._etag_for_http_url(source)

                        if old_etag == new_etag:
                            continue

                        self._download_tagged_http_resource(source, target,
                                etag=new_etag)
                    except DebianPackageCacheError as e:
                        self.log.error("Failed to retrieve {}: {}"
                                .format(source, str(e)))

                    # Remove old blob.
                    if old_etag:
                        os.unlink(os.path.join(os.path.dirname(target),
                            old_etag))
                #end for
            #end for
        #end for

        self._parse_package_list(what=what)
    #end function

    # PRIVATE

    def _parse_package_list(self, what=SOURCE|BINARY):
        pkg_types = []

        if what & self.SOURCE:
            pkg_types.append("source")
            self.source.clear()
        if what & self.BINARY:
            pkg_types.extend(["binary-{}".format(self.arch), "binary-all"])
            self.binary.clear()

        for component, base_url in self.sources_list:
            for pocket in self.pockets:
                for type_ in pkg_types:
                    if type_ == "source":
                        meta_gz = "Sources.gz"
                        cache = self.source
                    else:
                        meta_gz = "Packages.gz"
                        cache = self.binary
                    #end if

                    meta_file = os.path.join(self._cache_dir, self.release,
                        component, pocket, type_, meta_gz)

                    if not os.path.exists(meta_file):
                        continue

                    with ArchiveFileReader(meta_file, raw=True) as archive:
                        try:
                            next(iter(archive))
                        except StopIteration:
                            # The archive is empty.
                            continue

                        buf = archive\
                            .read_data()\
                            .decode("utf-8")

                        pool_base = re.match(
                            r"^(?P<pool_base>https?://.*?)/dists/.*$",
                            base_url
                        ).group("pool_base")

                        for chunk in re.split(r"\n\n+", buf, flags=re.MULTILINE):
                            chunk = chunk.strip()
                            if not chunk:
                                continue

                            meta_data = DebianPackageMetaData(
                                chunk, base_url=pool_base)

                            pkg_name    = meta_data["Package"]
                            pkg_version = meta_data["Version"]

                            cache\
                                .setdefault(pkg_name, DebianPackageDict())\
                                .setdefault(pkg_version, meta_data)
                        #end for
                    #end with
                #end for
            #end for
        #end for

        return (self.source, self.binary)
    #end function

    def _download_tagged_http_resource(self, source_url, target_file,
            etag="", connection_timeout=30):
        if not etag:
            etag = self._etag_for_http_url(source_url)

        blob_name = os.path.join(os.path.dirname(target_file), etag)
        try:
            request = urllib.request.Request(source_url, method="GET")
            with urllib.request.urlopen(request, timeout=connection_timeout)\
                    as response:
                with open(blob_name, 'wb+') as f:
                    for chunk in iter(
                            lambda: response.read(1024 * 1024), b""):
                        f.write(chunk)
                    #end for
                #end with
            #end with
        except (OSError, urllib.error.URLError) as e:
            if os.path.exists(blob_name):
                os.unlink(blob_name)
            raise DebianPackageCacheError(
                "failed to download http resource: {}".format(str(e))
            )
        #end try

        # Create temporary symlink to new blob.
        os.symlink(os.path.basename(blob_name), target_file + "$")

        # Atomically rename symlink (hopefully).
        os.rename(target_file + "$", target_file)
    #end function

    def _etag_for_http_url(self, url, connection_timeout=30):
        alphabet = \
            string.ascii_uppercase + \
            string.ascii_lowercase + \
            string.digits

        try:
            request = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(request, timeout=connection_timeout)\
                    as response:
                identifier1 = response.getheader("ETag", "")
                identifier2 = response.getheader(
                    "Last-Modified",
                    "".join([random.choice(alphabet) for i in range(16)])
                )
        except urllib.error.URLError as e:
            raise DebianPackageCacheError("failed to generate etag: {}"
                    .format(str(e)))

        sha256 = hashlib.sha256()
        sha256.update(identifier1.encode("utf-8"))
        sha256.update(identifier2.encode("utf-8"))

        return sha256.hexdigest()[:16]
    #end function

    def _etag_for_file(self, filename):
        if not os.path.islink(filename):
            return ""
        return os.path.basename(os.readlink(filename))
    #end function

#end class
