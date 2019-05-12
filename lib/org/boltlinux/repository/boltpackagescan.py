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
import logging
import functools
import urllib.error
import urllib.request
import tempfile

from org.boltlinux.repository.flaskinit import app, db
from org.boltlinux.repository.models import BinaryPackage, PackageEntry
from org.boltlinux.repository.repotask import RepoTask
from org.boltlinux.error import RepositoryError
from org.boltlinux.package.libarchive import ArchiveFileReader, ArchiveError

class BoltPackageScan(RepoTask):

    def __init__(self, config, verbose=True):
        super().__init__("bolt-package-scan")

        release = config.get("release", {})

        self._verbose      = verbose
        self._repositories = {}
        self._release      = release.get("id", "stable")

        for repo_info in config.get("repositories", []):
            self._repositories[repo_info["name"]] = repo_info

        self.log = logging.getLogger("org.boltlinux.repository")
    #end function

    def run_task(self):
        self.scan_packages()

    def scan_packages(self):
        with app.app_context():
            for pkg_obj in BinaryPackage.query.filter_by(needs_scan=True):
                if self.is_stopped():
                    return

                repo_name = pkg_obj.repo_name
                repo_info = self._repositories.get(repo_name)

                if not repo_info:
                    self.log.warning(
                        "Repository '%s' not found in configuration." %
                            repo_name)
                    continue
                #end if

                repo_url = repo_info["repo-url"]

                pkg_url = "/".join([repo_url, self._release, pkg_obj.libc,
                    pkg_obj.arch, pkg_obj.component, pkg_obj.filename])

                pkg_info_list = self._download_and_scan(pkg_url)

                for uname, gname, mode, pathname in pkg_info_list:
                    pkg_entry = PackageEntry(
                        binary_package_id = pkg_obj.id_,
                        uname    = uname,
                        gname    = gname,
                        mode     = mode,
                        pathname = pathname
                    )

                    db.session.add(pkg_entry)
                #end for

                pkg_obj.needs_scan = False
                db.session.commit()
            #end for
        #end with
    #end function

    # INTERNAL

    def _download_and_scan(self, url):
        pkg_name = url.rsplit("/", 1)[1]
        try:
            with urllib.request.urlopen(url) as response:
                with tempfile.TemporaryDirectory() as dirname:
                    archive_file = os.path.join(dirname, pkg_name)

                    with open(archive_file, "wb+") as f:
                        for chunk in iter(lambda: response.read(8192), b""):
                            f.write(chunk)
                    #end with

                    return self._scan_file(archive_file)
                #end with
            #end with
        except urllib.error.URLError as e:
            self.log.error("failed to retrieve {}: {}"
                    .format(url, str(e)))
    #end function

    def _scan_file(self, pkg_file):
        dirname   = os.path.dirname(pkg_file)
        data_file = None
        result    = []

        try:

            with ArchiveFileReader(pkg_file) as archive:
                for entry in archive:
                    if not entry.pathname.startswith("data.tar."):
                        continue

                    data_file = os.path.join(dirname, entry.pathname)

                    with open(data_file, "wb+") as f:
                        for chunk in iter(lambda: archive.read_data(4096), b""):
                            f.write(chunk)
                    #end with
                #end for
            #end with

            if not data_file:
                self.log("Corrupt package archive {} has no data file"
                        .format(pkg_file))
                return result

            with ArchiveFileReader(data_file) as archive:
                for entry in archive:
                    result.append([
                        entry.uname,
                        entry.gname,
                        entry.mode,
                        entry.pathname
                    ])
            #end with
        except (OSError, ArchiveError) as e:
            self.log.error("Failed to scan {}: {}".format(filename, str(e)))

        return result
    #end function

#end class

