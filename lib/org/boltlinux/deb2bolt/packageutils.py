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

class PackageUtilsMixin:

    IMPLICIT_PATHS = {
        "/",
        "/srv",
        "/etc",
        "/etc/skel",
        "/etc/profile.d",
        "/etc/opt",
        "/sbin",
        "/var",
        "/var/misc",
        "/var/spool",
        "/var/spool/mail",
        "/var/mail",
        "/var/cache",
        "/var/run",
        "/var/www",
        "/var/local",
        "/var/lib",
        "/var/tmp",
        "/var/opt",
        "/var/log",
        "/mnt",
        "/run",
        "/run/mount",
        "/home",
        "/sys",
        "/bin",
        "/dev",
        "/proc",
        "/media",
        "/lib",
        "/tmp",
        "/opt",
        "/boot",
        "/root",
        "/usr",
        "/usr/src",
        "/usr/include",
        "/usr/sbin",
        "/usr/bin",
        "/usr/share",
        "/usr/share/misc",
        "/usr/share/base-files",
        "/usr/share/zoneinfo",
        "/usr/share/terminfo",
        "/usr/share/doc",
        "/usr/share/locale",
        "/usr/share/man",
        "/usr/share/man/man7",
        "/usr/share/man/man2",
        "/usr/share/man/man8",
        "/usr/share/man/man4",
        "/usr/share/man/man6",
        "/usr/share/man/man5",
        "/usr/share/man/man1",
        "/usr/share/man/man3",
        "/usr/share/info",
        "/usr/local",
        "/usr/local/src",
        "/usr/local/include",
        "/usr/local/sbin",
        "/usr/local/bin",
        "/usr/local/share",
        "/usr/local/share/misc",
        "/usr/local/share/zoneinfo",
        "/usr/local/share/terminfo",
        "/usr/local/share/doc",
        "/usr/local/share/locale",
        "/usr/local/share/man",
        "/usr/local/share/man/man7",
        "/usr/local/share/man/man2",
        "/usr/local/share/man/man8",
        "/usr/local/share/man/man4",
        "/usr/local/share/man/man6",
        "/usr/local/share/man/man5",
        "/usr/local/share/man/man1",
        "/usr/local/share/man/man3",
        "/usr/local/share/info",
        "/usr/local/lib",
        "/usr/lib",
        "/usr/doc",
        "/usr/man",
        "/usr/info"
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

    def is_pkg_name_implicit(self, name):
        if name in ["libc6"]:
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
        if name in ["quilt", "lsb-release", "cdbs"]:
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
