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
from com.nonterra.bolt.debian.basepackage import BasePackageMixin
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

class BinaryPackage(BasePackageMixin):

    def __init__(self, content):
        try:
            self.parse_content(content)
        except:
            msg = "error parsing control file."
            raise ControlFileSyntaxError(msg)
        #end try
    #end function

    def load_content_spec(self, directory):
        pkg_name = self.fields["name"]
        content  = {}

        extensions = [".files", ".install", ".dirs", ".files.in",
                ".install.in", ".dirs.in"]
        install_file_list  = [pkg_name + ext for ext in extensions] \
                + ["files", "install", "dirs"]

        for filename in install_file_list:
            abs_path = os.path.join(directory, filename)
            if not os.path.exists(abs_path):
                continue

            parts = filename.split(".")
            if parts[-1] == "in":
                content_type = parts[-2]
            else:
                content_type = parts[-1]

            with open(abs_path, "r", encoding="utf-8") as f:
                lines = []
                for line in f.readlines():
                    line = line.strip()

                    if not line:
                        continue

                    m = re.match(r"^(\S+)\s+(\S+)$", line)
                    if m:
                        line = m.group(1)
                    if "share/doc" in line:
                        continue
                    if "share/man" in line:
                        continue

                    line = re.sub(re.escape("${DEB_HOST_MULTIARCH}"), "", line)
                    line = re.sub(r"^(/)?(s)?bin", r"\1usr/\2bin", line)
                    line = re.sub(r"^(/)?lib", r"\1usr/lib", line)
                    line = re.sub(r"usr/lib/\*/", r"usr/lib/", line)
                    line = os.path.normpath(line)

                    lines.append(line)
                #end for

                content[content_type] = lines
            #end with
        #end for

        files = content.get("files", []) + content.get("install", [])
        files = sorted(set(files))
        files = [(os.sep + f).replace(os.sep*2, os.sep) for f in files]
        dirs  = sorted(set(content.get("dirs", [])))
        dirs  = [(os.sep + d).replace(os.sep*2, os.sep) for d in dirs ]
        self.fields["files"], self.fields["dirs"] = files, dirs
    #end function

    def as_xml(self, indent=0):
        install_deps = ""
        for dep in self.get("depends", []) + self.get("pre-depends", []):
            if dep[1]:
                install_deps += " " * 8
                install_deps += "<package name=\"%s\" version=\"%s\"/>\n" \
                        % (dep[0], dep[1])
            else:
                install_deps += " " * 8 + "<package name=\"%s\"/>\n" % dep[0]
        #end for

        contents = ""
        for d in self.get("dirs", []):
            contents += " " * 8 + "<dir src=\"%s\"/>\n" % d
        for f in self.get("files", []):
            contents += " " * 8 + "<file src=\"%s\"/>\n" % f

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
