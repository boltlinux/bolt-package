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
from org.boltlinux.package.progressbar import ProgressBar

class SourceCache:

    def __init__(self, cache_dir, repo_config, verbose=True):
        self.cache_dir   = cache_dir
        self.repo_config = repo_config
        self.verbose     = verbose
    #end function

    def find_and_retrieve(self, pkg_name, version, filename, sha256sum=None):
        if self.verbose:
            sys.stdout.write("Retrieving '%s' (%s): %s\n" %
                    (pkg_name, version, filename))

        pkg = self.fetch_from_cache(pkg_name, version, filename, sha256sum)
        if pkg:
            if self.verbose:
                msg = "[" + "#" * 26 + " CACHED " + "#" * 26 + "] 100%\n"
                sys.stdout.write(msg)
            return pkg
        #end if

        return self.fetch_from_repo(pkg_name, version, filename, sha256sum)
    #end function

    def fetch_from_cache(self, pkg_name, version, filename, sha256sum=None):
        if pkg_name.startswith("lib"):
            first_letter = pkg_name[3]
        else:
            first_letter = pkg_name[0]
        #end if

        rel_path = os.sep.join([first_letter, pkg_name, version, filename])
        abs_path = os.path.join(self.cache_dir, rel_path)

        if not os.path.exists(abs_path):
            return None
        if not sha256sum:
            return abs_path

        with open(abs_path, "rb") as fp:
            h = hashlib.sha256()

            while True:
                buf = fp.read(1024*1024)
                if not buf:
                    break
                h.update(buf)
            #end while

            real_sha256sum = h.hexdigest()
        #end with

        if sha256sum == real_sha256sum:
            return abs_path

        return None
    #end function

    def fetch_from_repo(self, pkg_name, version, filename, sha256sum=None):
        if pkg_name.startswith("lib"):
            first_letter = pkg_name[3]
        else:
            first_letter = pkg_name[0]
        #end if

        rel_path = os.sep.join([first_letter, pkg_name, version, filename])
        abs_path = os.path.join(self.cache_dir, rel_path)

        for repo in self.repo_config:
            source_url = repo["url"]    + "/"    + rel_path
            target_url = self.cache_dir + os.sep + rel_path

            h = hashlib.sha256()

            try:
                with urllib.request.urlopen(source_url) as response:
                    if response.length:
                        progress_bar = ProgressBar(response.length)
                    else:
                        progress_bar = None
                    #end if

                    bytes_read = 0
                    if self.verbose and progress_bar:
                        progress_bar(bytes_read)

                    os.makedirs(os.path.dirname(target_url), exist_ok=True)
                    with open(target_url, "wb+") as outfile:
                        while True:
                            buf = response.read(1024*1024)
                            if not buf:
                                break

                            h.update(buf)
                            bytes_read += len(buf)
                            outfile.write(buf)

                            if self.verbose and progress_bar:
                                progress_bar(bytes_read)
                        #end while
                    #end with
                #end with
            except urllib.error.URLError as e:
                sys.stderr.write("  Warning: failed to retrieve\n  "
                    "%s\n  Reason: %s\n" % (source_url, e.reason))
                continue
            #end try

            if sha256sum and sha256sum != h.hexdigest():
                if self.verbose:
                    sys.stdout.write("Invalid checksum!\n")
                continue
            #end if

            return target_url
        #end for

        return None
    #end function

#end class
