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
import sys
import re
import stat
import locale
import subprocess
import urllib.request

import org.boltlinux.package.libarchive as libarchive
from org.boltlinux.error import NotFound, PackagingError, NetworkError, \
        BoltValueError

class PackageUtilsMixin:

    IMPLICIT_PATHS = {
        "/": 1,
        "/srv": 1,
        "/etc": 1,
        "/etc/skel": 1,
        "/etc/profile.d": 1,
        "/etc/opt": 1,
        "/sbin": 1,
        "/var": 1,
        "/var/misc": 1,
        "/var/spool": 1,
        "/var/spool/mail": 1,
        "/var/mail": 1,
        "/var/cache": 1,
        "/var/run": 1,
        "/var/www": 1,
        "/var/local": 1,
        "/var/lib": 1,
        "/var/tmp": 1,
        "/var/opt": 1,
        "/var/log": 1,
        "/mnt": 1,
        "/run": 1,
        "/run/mount": 1,
        "/home": 1,
        "/sys": 1,
        "/bin": 1,
        "/dev": 1,
        "/proc": 1,
        "/media": 1,
        "/lib": 1,
        "/tmp": 1,
        "/opt": 1,
        "/boot": 1,
        "/root": 1,
        "/usr": 1,
        "/usr/src": 1,
        "/usr/include": 1,
        "/usr/sbin": 1,
        "/usr/bin": 1,
        "/usr/share": 1,
        "/usr/share/misc": 1,
        "/usr/share/base-files": 1,
        "/usr/share/zoneinfo": 1,
        "/usr/share/terminfo": 1,
        "/usr/share/doc": 1,
        "/usr/share/locale": 1,
        "/usr/share/man": 1,
        "/usr/share/man/man7": 1,
        "/usr/share/man/man2": 1,
        "/usr/share/man/man8": 1,
        "/usr/share/man/man4": 1,
        "/usr/share/man/man6": 1,
        "/usr/share/man/man5": 1,
        "/usr/share/man/man1": 1,
        "/usr/share/man/man3": 1,
        "/usr/share/info": 1,
        "/usr/local": 1,
        "/usr/local/src": 1,
        "/usr/local/include": 1,
        "/usr/local/sbin": 1,
        "/usr/local/bin": 1,
        "/usr/local/share": 1,
        "/usr/local/share/misc": 1,
        "/usr/local/share/zoneinfo": 1,
        "/usr/local/share/terminfo": 1,
        "/usr/local/share/doc": 1,
        "/usr/local/share/locale": 1,
        "/usr/local/share/man": 1,
        "/usr/local/share/man/man7": 1,
        "/usr/local/share/man/man2": 1,
        "/usr/local/share/man/man8": 1,
        "/usr/local/share/man/man4": 1,
        "/usr/local/share/man/man6": 1,
        "/usr/local/share/man/man5": 1,
        "/usr/local/share/man/man1": 1,
        "/usr/local/share/man/man3": 1,
        "/usr/local/share/info": 1,
        "/usr/local/lib": 1,
        "/usr/lib": 1,
        "/usr/doc": 1,
        "/usr/man": 1,
        "/usr/info": 1
    }

    def is_path_implicit(self, path):
        return path in PackageUtilsMixin.IMPLICIT_PATHS

    def is_doc_path(self, path):
        doc_prefixes = [
            "/usr/share/doc/",
            "/usr/share/man/",
            "/usr/share/info/"
        ]
        for prefix in doc_prefixes:
            if path == prefix.rstrip(os.sep) or path.startswith(prefix):
                return True
        return False
    #end function

    def is_l10n_path(self, path):
        return path == "/usr/share/locale" or \
                path.startswith("/usr/share/locale/")

    def is_menu_path(self, path):
        return path == "/usr/share/menu" or path.startswith("/usr/share/menu/")

    def is_mime_path(self, path):
        return path == "/usr/lib/mime" or path.startswith("/usr/lib/mime/")

    def is_misc_unneeded(self, path):
        unneeded_prefixes = [
            "/usr/share/lintian/",
            "/usr/share/bash-completion/"
        ]
        for prefix in unneeded_prefixes:
            if path == prefix.rstrip(os.sep) or path.startswith(prefix):
                return True
        return False
    #end function

    def is_pkg_name_debian_specific(self, name):
        if name.startswith("dpkg"):
            return True
        if name.startswith("debhelper"):
            return True
        if name.endswith("debconf"):
            return True
        if name.startswith("dh-"):
            return True
        if name in ["quilt", "lsb-release"]:
            return True
        return False
    #end function

    def fix_path(self, path):
        if path in ["./", "/"]:
            return "/"

        path = path \
            .lstrip(".") \
            .rstrip("/")
        if not path[0] == "/":
            path = "/" + path
        path = re.sub(re.escape("${DEB_HOST_MULTIARCH}"), "", path)
        path = re.sub(r"^(/)?(s)?bin", r"\1usr/\2bin", path)
        path = re.sub(r"^(/)?lib", r"\1usr/lib", path)
        path = re.sub(r"usr/lib/\*/", r"usr/lib/", path)
        path = re.sub(r"usr/lib/[^/]+-linux-gnu(/|$)", r"usr/lib/\1", path)
        path = os.path.normpath(path)

        return path
    #end function

#end class
