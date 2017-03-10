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
import stat
import sys
from com.nonterra.bolt.debian.basepackage import BasePackageMixin
from com.nonterra.bolt.debian.packageutils import PackageUtilsMixin
from com.nonterra.bolt.debian.error import ControlFileSyntaxError

BINARY_PKG_XML_TEMPLATE = """\
<?xml version="1.0" encoding="utf-8"?>
<package name="%(binary_name)s" section="%(section)s">
    <description>
        <summary>%(summary)s</summary>
        <p>
%(description)s
        </p>
    </description>

    <requires>
%(install_deps)s\
    </requires>

    <contents>
%(contents)s\
    </contents>
</package>
"""

class BinaryPackage(BasePackageMixin, PackageUtilsMixin):

    def __init__(self, content):
        try:
            self.parse_content(content)
        except:
            msg = "error parsing control file."
            raise ControlFileSyntaxError(msg)
        #end try
    #end function

    def load_content_spec(self, debdir, pkg_name, pkg_version,
            use_network=True):
        sys.stdout.write("Trying to figure out '%s' contents ...\n" % pkg_name)
        if use_network:
            self.contents = self.get_content_spec_via_package_pool(
                    pkg_name, pkg_version)
        else:
            self.contents = self.get_content_spec_local_guesswork(
                    debdir, pkg_name, pkg_version)
        #end if
    #end function

    def as_xml(self, indent=0):
        self.contents.sort()

        install_deps = ""
        for dep in self.get("depends", []) + self.get("pre-depends", []):
            pkg_name, pkg_version = dep

            if self.is_pkg_name_debian_specific(pkg_name):
                continue

            if pkg_version:
                install_deps += " " * 8
                install_deps += "<package name=\"%s\" version=\"%s\"/>\n" \
                        % (pkg_name, pkg_version)
            else:
                install_deps += " " * 8 + "<package name=\"%s\"/>\n" % pkg_name
        #end for

        contents = ""
        for entry in self.contents:
            entry_path,  \
            entry_type,  \
            entry_mode,  \
            entry_uname, \
            entry_gname = entry

            if self.is_doc_path(entry_path):
                continue
            if self.is_l10n_path(entry_path):
                continue
            if self.is_menu_path(entry_path):
                continue
            if self.is_mime_path(entry_path):
                continue
            if self.is_misc_unneeded(entry_path):
                continue

            contents += \
                " " * 8 + \
                '<%s src="%s"' % ("dir" if entry_type == stat.S_IFDIR \
                    else "file", entry_path)

            if entry_type == stat.S_IFDIR:
                default_mode = 0o755
            elif entry_type == stat.S_IFLNK:
                default_mode = 0o777
            elif entry_type == stat.S_IFREG:
                if "/bin/" in entry_path or "/sbin/" in entry_path:
                    default_mode = 0o755
                else:
                    default_mode = 0o644
                #end if
            #end if

            if entry_mode and entry_mode != default_mode:
                contents += ' mode="%04o"' % entry_mode
            if entry_uname and entry_uname != "root":
                contents += ' user="%s"'   % entry_uname
            if entry_gname and entry_gname != "root":
                contents += ' group="%s"'  % entry_gname

            contents += '/>\n'
        #end for

        info_set = {
            "binary_name": self.get("name"),
            "section": self.get("section"),
            "summary": self.get("summary"),
            "description": self.get("description", ""),
            "install_deps": install_deps,
            "contents": contents
        }

        return BINARY_PKG_XML_TEMPLATE % info_set
    #end function

#end class
