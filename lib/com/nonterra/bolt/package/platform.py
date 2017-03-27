# -*- encoding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2016 Tobias Koch <tobias.koch@nonterra.com>
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

class Platform:

    CONFIG_GUESS = '/usr/share/misc/config.guess'

    @staticmethod
    def build_flags():
        build_flags = {}

        if "linux" in Platform.kernel_name().lower() and \
                os.path.exists("/etc/debian_version"):
            return Platform.__dpkg_build_flags()
        #end if

        if Platform.find_executable("gcc"):
            build_flags["CFLAGS"]   = "-g -O2 -fstack-protector-strong -Wformat -Werror=format-security"
            build_flags["CXXFLAGS"] = "-g -O2 -fstack-protector-strong -Wformat -Werror=format-security"
            build_flags["CPPFLAGS"] = "-Wdate-time -D_FORTIFY_SOURCE=2"
            build_flags["LDFLAGS"]  = "-Wl,-z,relro"
        #end if

        return build_flags
    #end function

    @staticmethod
    def num_cpus():
        cpu_info_file = "/proc/cpuinfo"
        num_cpus = 0

        if os.path.exists(cpu_info_file):
            with open(cpu_info_file, "r", encoding="utf-8") as fp:
                for line in fp:
                    if re.match(r"processor\s*:\s*\d+", line):
                        num_cpus += 1
                #end for
            #end with
        else:
            num_cpus = 1
        #end if

        return num_cpus
    #end function

    @staticmethod
    def find_executable(executable_name):
        search_path = os.environ.get("PATH", "").split(os.pathsep) + \
                ["/bin", "/sbin", "/usr/bin", "/usr/sbin"]

        for path in search_path:
            location = os.path.join(path, executable_name)
            if os.path.exists(location):
                return location
        #end for

        return None
    #end function

    @staticmethod
    def config_guess():
        preferred_encoding = locale.getpreferredencoding(False)
        gcc = Platform.find_executable("gcc")

        if gcc:
            return subprocess.run([gcc, "-dumpmachine"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL)\
                            .stdout\
                            .decode(preferred_encoding)\
                            .strip()
        #end if

        if os.path.exists(Platform.CONFIG_GUESS):
            return subprocess.run([Platform.CONFIG_GUESS],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL)\
                            .stdout\
                            .decode(preferred_encoding)\
                            .strip()
        #end if

        return ""
    #end function

    @staticmethod
    def kernel_name():
        uname = Platform.find_executable("uname")

        if not uname:
            return ""

        preferred_encoding = locale.getpreferredencoding(False)
        return subprocess.run([uname, "-s"], stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL).stdout\
                        .decode(locale.getpreferredencoding(False))\
                        .strip()
    #end function

    # HIDDEN

    @staticmethod
    def __dpkg_build_flags():
        build_flags = {}
        dpkg_buildflags = Platform.find_executable("dpkg-buildflags")

        if not dpkg_buildflags:
            return build_flags

        preferred_encoding = locale.getpreferredencoding(False)

        for flag in subprocess.run([dpkg_buildflags, "--list"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)\
                        .stdout.decode(preferred_encoding).splitlines():
            flag = flag.strip()

            if not flag:
                continue

            value = subprocess.run([dpkg_buildflags, "--get", flag],
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)\
                            .stdout.decode(preferred_encoding).strip()

            value = re.sub(r"\s*-fdebug-prefix-map=\S+\s*", " ", value)
            build_flags[flag] = value
        #end for

        return build_flags
    #end function

#end class
