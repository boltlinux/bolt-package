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
import tempfile

from org.boltlinux.deb2bolt.debiansource import DebianSource

class Deb2BoltPackageConverter:

    def __init__(self, pkg_cache, release="stable", arch="amd64"):
        self._release = release
        self._arch = arch
        self._cache = pkg_cache
    #end function

    def convert(self, pkg_name, target_dir=".", maintainer_info=None,
            run_rules=None, do_load_contents=True):
        target_dir = os.path.abspath(target_dir)

        with tempfile.TemporaryDirectory() as tmpdir:
            deb_source = DebianSource(
                self._cache,
                pkg_name,
                release=self._release,
                arch=self._arch,
                work_dir=tmpdir
            )

            deb_source\
                .download()\
                .unpack()\
                .run_rules(run_rules)

            deb_source.copy_sources_and_patches(target_dir)
            deb_source.parse_control_file()

            if do_load_contents:
                deb_source.build_content_spec()

            deb_source.to_bolt(
                target_dir,
                maintainer_info=maintainer_info
            )
        #end with
    #end function

#end class
