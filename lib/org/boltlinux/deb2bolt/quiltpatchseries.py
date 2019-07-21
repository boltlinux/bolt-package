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

import org.boltlinux.toolbox.libarchive as libarchive

from org.boltlinux.toolbox.libarchive import ArchiveFileWriter
from org.boltlinux.error import BoltError

class QuiltPatchSeries:

    def __init__(self):
        self.patches = []

    def __len__(self):
        return len(self.patches)

    def __bool__(self):
        return len(self.patches) != 0

    def __iter__(self):
        for p in self.patches:
            yield p
    #end function

    def append(self, item):
        self.patches.append(item)

    def insert(self, pos, item):
        self.patches.insert(pos, item)

    def read_patches(self, series_file):
        if not os.path.isfile(series_file):
            raise BoltError("No such file: {}".format(series_file))

        with open(series_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("#"):
                    continue
                self.patches.append(line)
            #end for
        #end with
    #end function

    def as_xml(self, indent=0):
        if not self.patches:
            return ""

        buf = '<patches>\n'
        buf += '    <patchset subdir="sources">\n'
        for p in self.patches:
            p = re.sub(r"\s+-p\d+\s*$", r"", p)
            buf += '        <file src="patches/%s"/>\n' % p
        buf += '    </patchset>\n'
        buf += '</patches>'

        return re.sub(r"^", " " * 4 * indent, buf, flags=re.M)
    #end function

    def create_tarball(self, patch_dir, tarfile):
        """Creates a gzip-compressed tarball and writes the contents to the
        filename specified in tarfile."""

        with ArchiveFileWriter(tarfile, libarchive.FORMAT_TAR_USTAR,
                libarchive.COMPRESSION_GZIP) as archive:
            for p in self.patches:
                # Remove extra parameter, e.g. -p1
                p = re.sub(r"\s+-p\d+\s*$", r"", p)

                patch_abs_path = os.path.join(patch_dir, p)
                patch_pathname = os.path.join("patches", p)

                archive.add_file(patch_abs_path, pathname=patch_pathname,
                        uname="root", gname="root")
            #end for
        #end with

        size      = os.path.getsize(tarfile)
        sha256sum = self._file_sha256_sum(tarfile)

        return (sha256sum, size)
    #end function

    # PRIVATE

    def _file_sha256_sum(self, filename):
        h = hashlib.sha256()
        with open(filename, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()
    #end function

#end class
