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
import hashlib
import logging
import urllib.request

from org.boltlinux.error import BoltError, NetworkError
from org.boltlinux.toolbox.progressbar import ProgressBar
from org.boltlinux.toolbox.downloader import Downloader

LOGGER = logging.getLogger(__name__)

class SourceCache:

    def __init__(self, cache_dir, repo_config, release="stable", verbose=True):
        self.cache_dir   = cache_dir
        self.repo_config = repo_config
        self.release     = release
        self.verbose     = verbose
    #end function

    def find_and_retrieve(self, repo_name, pkg_name, version, filename,
            sha256sum=None):
        pkg = self.fetch_from_cache(
            repo_name, pkg_name, version, filename, sha256sum
        )

        if pkg:
            return pkg

        return self.fetch_from_repo(
            repo_name, pkg_name, version, filename, sha256sum
        )
    #end function

    def fetch_from_cache(self, repo_name, pkg_name, version, filename,
            sha256sum=None):
        if pkg_name.startswith("lib"):
            first_letter = pkg_name[3]
        else:
            first_letter = pkg_name[0]
        #end if

        rel_path = os.sep.join(
            [
                self.release,
                repo_name,
                first_letter,
                pkg_name,
                version,
                filename
            ]
        )
        abs_path = os.path.join(self.cache_dir, rel_path)

        if not os.path.exists(abs_path):
            return None
        if not sha256sum:
            return abs_path

        h = hashlib.sha256()

        with open(abs_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        #end with

        if sha256sum == h.hexdigest():
            return abs_path

        return None
    #end function

    def fetch_from_repo(self, repo_name, pkg_name, version, filename,
            sha256sum=None):
        downloader = Downloader(progress_bar_class=ProgressBar)

        if pkg_name.startswith("lib"):
            first_letter = pkg_name[3]
        else:
            first_letter = pkg_name[0]

        rel_path = os.sep.join([first_letter, pkg_name, version, filename])

        try:
            repo = self.repo_config[repo_name]
        except KeyError:
            raise BoltError(
                "repository '{}' not found in configuration."
                .format(repo_name)
            )
        #end try

        source_url = "/".join([
            repo["repo-url"],
            self.release,
            repo_name,
            "sources",
            rel_path
        ])

        target_url = os.sep.join([
            self.cache_dir, self.release, repo_name, rel_path
        ])

        h = hashlib.sha256()

        LOGGER.info("retrieving {}".format(source_url))
        try:
            os.makedirs(os.path.dirname(target_url), exist_ok=True)

            with open(target_url, "wb+") as f:
                for chunk in downloader.get(source_url, digest=h):
                    f.write(chunk)
        except urllib.error.URLError as e:
            raise NetworkError(
                "failed to retrieve {}: {}".format(source_url, e.reason)
            )

        if sha256sum and sha256sum != h.hexdigest():
            raise BoltError("file {} has invalid checksum!".format(target_url))

        return target_url
    #end function

#end class
