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

import re

from org.boltlinux.error import BoltError
from org.boltlinux.package.xpkg import BaseXpkg

class DebianPackageMetaDataError(BoltError):
    pass

class DebianPackageVersion:

    def __init__(self, version):
        self._version = version

    def __str__(self):
        return self._version

    def __lt__(self, other):
        return BaseXpkg.compare_versions(self._version, other._version) == -1

#end class

class DebianPackageMetaData:

    def __init__(self, string="", base_url=""):
        self._fields   = self._parse_meta_data(string)
        self._base_url = base_url

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
            "Installed-Size",
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

    @property
    def url(self):
        return self._base_url + "/" + self._fields["Filename"]

    # PRIVATE

    def _parse_meta_data(self, string):
        fields = {}

        key = None
        val = None

        for line in string.strip().splitlines():
            if re.match(r"^\s+.*?$", line):
                if key is None:
                    raise DebianPackageMetaDataError(
                            "invalid control file syntax.")

                val.append(line.strip())
            else:
                if not ":" in line:
                    raise DebianPackageMetaDataError(
                            "invalid control file syntax.")

                if key is not None:
                    fields[key] = "\n  ".join(val)

                k, v = [item.strip() for item in line.split(":", 1)]

                key = k
                val = [v,]
            #end if
        #end for

        if key is not None:
            fields[key] = "\n  ".join(val)

        m = re.match(r".*?\((?P<version>.*?)\)\s*$", fields.get("Source", ""))
        if m:
            fields["Version"] = m.group("version")

        return fields
    #end function

#end class
