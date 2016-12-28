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
        # PACKAGE LIST

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
                            self.packages[name] = meta_data["version"]
                    #end for
                #end if
            #end if
        #end for

        # FOR VERSION COMPARISON

        self._char_vals = {
            "~": 0,
            " ": 1,
            "-": 2,
            "+": 3,
            ".": 4
        }

        for ascii_val in range(ord("A"), ord("Z") + 1):
            self._char_vals[chr(ascii_val)] = ascii_val
        for ascii_val in range(ord("a"), ord("z") + 1):
            self._char_vals[chr(ascii_val)] = ascii_val
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

    def compare_versions(self, a, b):
        m = re.match(r"^(?:(\d+):)?([-+:~.a-zA-Z0-9]+?)(?:-([^-]+))?$", a)
        epoch_a, version_a, rev_a = m.groups(default="") if m else ("", "", "")
        m = re.match(r"^(?:(\d+):)?([-+:~.a-zA-Z0-9]+?)(?:-([^-]+))?$", b)
        epoch_b, version_b, rev_b = m.groups(default="") if m else ("", "", "")

        epoch_a = int(epoch_a) if epoch_a else 0
        epoch_b = int(epoch_b) if epoch_b else 0

        # compare epochs
        if epoch_a > epoch_b:
            return +1
        if epoch_a < epoch_b:
            return -1

        nondigit  = 0
        digit     = 1

        mode = nondigit
        for v_a, v_b in [(version_a, version_b), (rev_a, rev_b)]:
            while v_a or v_b:
                if mode == nondigit:
                    m = re.match(r"^\D+", v_a)
                    p_a = m.group() if m else ""
                    m = re.match(r"^\D+", v_b)
                    p_b = m.group() if m else ""

                    len_a = len(p_a)
                    len_b = len(p_b)
                    v_a = v_a[len_a:]
                    v_b = v_b[len_b:]

                    if len_a != len_b:
                        if len_a > len_b:
                            p_b += " " * (len_a - len_b)
                        else:
                            p_a += " " * (len_b - len_a)
                    #end if

                    for c_a, c_b in zip(p_a, p_b):
                        if self._char_vals[c_a] > self._char_vals[c_b]:
                            return +1
                        if self._char_vals[c_a] < self._char_vals[c_b]:
                            return -1
                    #end for

                    mode = digit
                else:
                    m = re.match(r"^\d+", v_a)
                    p_a = m.group() if m else "0"
                    m = re.match(r"^\d+", v_b)
                    p_b = m.group() if m else "0"

                    v_a = v_a[len(p_a):]
                    v_b = v_b[len(p_b):]
                    val_a = int(p_a)
                    val_b = int(p_b)

                    if val_a > val_b:
                        return +1
                    if val_a < val_b:
                        return -1

                    mode = nondigit
                #end if
            #end while
        #end for

        return 0
    #end function

    def installed_version_meets_condition(self, package_name, condition=None):
        installed_version = self.installed_version_of_package(package_name)

        if not installed_version:
            return False
        if not condition:
            return True

        m = re.match(r"^\s*(<<|<=|=|>=|>>)\s*(\S+)\s*$", condition)

        if not m:
            msg = "invalid dependency specification '%s'" % condition
            raise ValueError(msg)
        #end if

        operator = m.group(1)
        version  = m.group(2)

        operator_map = {
            "<<": [-1],
            "<=": [-1, 0],
            "=":  [0],
            ">=": [+1, 0],
            ">>": [+1]
        }

        expected_result = operator_map[operator]

        if self.compare_versions(installed_version, version) in expected_result:
            return True

        return False
    #end function

#end class
