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

from tempfile import TemporaryDirectory
from org.boltlinux.package.libarchive import ArchiveFileReader
from org.boltlinux.error import BoltSyntaxError

class PackageMetaData:

    def __init__(self, string):
        self._fields = self.__parse_meta_data(string)

    def __getitem__(self, key):
        return self._fields[key]

    def __setitem__(self, key, value):
        self._fields[key] = value

    def as_string(self):
        rval = ""

        keys = [
            "Package",
            "Source",
            "Version",
            "Maintainer",
            "Architecture",
            "Depends",
            "Pre-Depends",
            "Recommends",
            "Suggests",
            "Breaks",
            "Conflicts",
            "Provides",
            "Replaces",
            "Enhances",
            "Description",
            "Section",
            "Filename",
            "Size",
            "SHA256"
        ]

        for k in keys:
            if k in self._fields:
                rval += "{key}: {value}\n"\
                            .format(key=k, value=self._fields[k])
            #end if
        #end for

        return rval
    #end function

    # PRIVATE

    def __parse_meta_data(self, string):
        fields = {}

        key = None
        val = None

        for line in string.strip().splitlines():
            if re.match(r"^\s+.*?$", line):
                if key is None:
                    raise BoltSyntaxError("invalid control file syntax.")

                val.append(line.strip())
            else:
                if not ":" in line:
                    raise BoltSyntaxError("invalid control file syntax.")

                if key is not None:
                    fields[key] = "\n  ".join(val)

                k, v = [item.strip() for item in line.split(":", 1)]

                key = k
                val = [v,]
            #end if
        #end for

        if key is not None:
            fields[key] = "\n  ".join(val)

        return fields
    #end function

#end class

class RepoIndexer:

    def __init__(self, repo_dir):
        self._repo_dir = repo_dir

    def scan(self):
        for path, dirs, files in os.walk(self._repo_dir, followlinks=True):

            for filename in files:
                if not filename.endswith(".bolt"):
                    continue

                abs_path = os.path.join(path, filename)

                try:
                    control_data = self.extract_control_data(abs_path)
                except BoltSyntaxError:
                    pass

                print(control_data.as_string())
            #end for
        #end for
    #end function

    def extract_control_data(self, filename):
        meta_data = None

        with TemporaryDirectory() as tmpdir:
            with ArchiveFileReader(filename) as archive:
                for entry in archive:
                    if not entry.pathname.startswith("control.tar."):
                        continue

                    data_file = os.path.join(tmpdir, entry.pathname)

                    with open(data_file, "wb+") as outfile:
                        while True:
                            buf = archive.read_data(4096)
                            if not buf:
                                break
                            outfile.write(buf)
                        #end while
                    #end with

                    pool_path = re.sub(r"^" + re.escape(self._repo_dir) + r"/*",
                            "", filename)

                    meta_data = PackageMetaData(
                        self.__extract_control_data(data_file))

                    meta_data["Filename"] = pool_path

                    break
                #end for
            #end with
        #end with

        meta_data["SHA256"] = self.__compute_sha256_sum(filename)
        meta_data[ "Size" ] = os.path.getsize(filename)

        return meta_data
    #end function

    # PRIVATE

    def __extract_control_data(self, filename):
        with ArchiveFileReader(filename) as archive:
            for entry in archive:
                if not entry.pathname == "control":
                    continue

                meta_data = archive\
                    .read_data()\
                    .decode("utf-8")

                meta_data = \
                    re.sub(r"^\s+.*$", "", meta_data, flags=re.MULTILINE)

                return meta_data.strip()
            #end for
        #end with
    #end function

    def __compute_sha256_sum(self, filename):
        sha256 = hashlib.sha256()

        with open(filename, "rb") as f:
            while True:
                buf = f.read(4096)

                if not buf:
                    break

                sha256.update(buf)
            #end while
        #end with

        return sha256.hexdigest()
    #end function

#end class

