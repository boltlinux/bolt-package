# -*- encoding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2016 Nonterra Software Solutions
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
import subprocess
import locale

class Dpkg:

    STATUS_FILE = '/var/lib/dpkg/status'

    def __init__(self):
        self.packages = {}
        self.preferred_encoding = locale.getpreferredencoding(False)

        with open(Dpkg.STATUS_FILE, "r", encoding="utf-8") as fp:
            buf = fp.read()

        package_list = re.split(r"\n\n+", buf , flags=re.MULTILINE)

        for pkg in package_list:
            meta_data = {}

            for line in pkg.splitlines():
                m = re.match(
                    r"^(Package|Version|Provides|Status):\s*(.*)",
                    line
                )
                if m:
                    meta_data[m.group(1).lower()] = m.group(2).strip()
            #end for

            if re.match(r"install\s+ok\s+installed",
                    meta_data.get("status", "")):
                self.packages[meta_data["package"]] = meta_data["version"]

                if "provides" in meta_data:
                    provides = [p.strip() for p in \
                            meta_data["provides"].split(",")]
                    for name in provides:
                        if not name in self.packages:
                            self.packages[name] = ''
                    #end for
                #end if
            #end if
        #end for
    #end function

    def which_package_provides(self, filename):
        result  = None
        abspath = os.path.abspath(filename)
        cmd     = ["dpkg", "-S", abspath]

        try:
            procinfo = subprocess.run(cmd, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, check=True)
        except subprocess.CalledProcessError:
            return None
        #end try

        return procinfo.stdout\
            .decode(self.preferred_encoding)\
            .strip()\
            .split(":", 1)[0]
    #end function

    def installed_version_of_package(self, package_name):
        return self.packages.get(package_name, None)
    #end function

    def installed_version_meets_condition(self, package_name, condition=None):
        installed_version = self.installed_version_of_package(package_name)

        if not installed_version:
            return False
        if not condition:
            return True

        m = re.match(r"^(<<|<=|=|>=|>>)\s*(\S+)$", condition)

        if not m:
            msg = "invalid dependency specification '%s'" % condition
            raise ValueError(msg)
        #end if

        operator = m.group(1)
        version  = m.group(2)

        operator_map = {
            "<<": "lt-nl",
            "<=": "le-nl",
            "=":  "eq",
            ">=": "ge-nl",
            ">>": "gt-nl"
        }

        operator = operator_map[operator]

        cmd = ["dpkg", "--compare-versions",
                installed_version, operator, version]

        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, check=True)
        except subprocess.CalledProcessError:
            return False
        #end try

        return True
    #end function

#end class
