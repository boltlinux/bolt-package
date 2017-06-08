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

class PatchSeries:

    def __init__(self, series_file=None):
        self.patches = []
        self.patch_subdir = "patches"

        if series_file and os.path.exists(series_file):
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

            self.patch_subdir = os.path.basename(os.path.dirname(series_file))
        #end if
    #end function

    def __iter__(self):
        for p in self.patches:
            yield p
    #end function

    def as_xml(self, indent=0):
        if not self.patches:
            return ""

        buf  = '\n'
        buf += '<patches>\n'
        buf += '    <patchset subdir="sources">\n'
        for p in self.patches:
            p = re.sub(r"\s+-p\d+\s*$", r"", p)
            buf += '        <file src="patches/%s"/>\n' % p
        buf += '    </patchset>\n'
        buf += '</patches>'

        return re.sub(r"^", " " * 4 * indent, buf, flags=re.M) + "\n"
    #end function

#end class
