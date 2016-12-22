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
from com.nonterra.bolt.debian.changelog import Changelog
from com.nonterra.bolt.debian.patchseries import PatchSeries
from com.nonterra.bolt.debian.binarypackage import BinaryPackage
from com.nonterra.bolt.debian.basepackage import BasePackageMixin

PKG_RULES_XML_TEMPLATE = """\
<?xml version="1.0" encoding="utf-8"?>
<rules>
    <prepare>
    <![CDATA[

cd $BOLT_BUILD_DIR
$BOLT_SOURCE_DIR/configure \\
    --prefix=/usr \\
    --disable-nls

    ]]>
    </prepare>

    <build>
    <![CDATA[

cd $BOLT_BUILD_DIR
make -j$BOLT_PARALLEL_JOBS

    ]]>
    </build>

    <install>
    <![CDATA[

cd $BOLT_BUILD_DIR
make DESTDIR=$BOLT_INSTALL_DIR install

    ]]>
    </install>
</rules>
"""

SOURCE_PKG_XML_TEMPLATE = """\
<?xml version="1.0" encoding="utf-8"?>
<control xmlns:xi="http://www.w3.org/2001/XInclude">
    <defines>
        <def name="BOLT_BUILD_DIR" value="build"/>
    </defines>

    <source name="%(source_name)s" architecture-independent="%(arch_indep)s">
        <description>
            <summary>%(summary)s</summary>
            <p>
%(description)s
            </p>
        </description>

        <sources>
            <file src="%(source_name)s-%(upstream_version)s.tar.gz" subdir="sources"
                sha256sum=""/>
            <file src="patches.01.tar.gz" subdir="patches"
                sha256sum=""/>
        </sources>
%(patches)s
        <requires>
%(build_deps)s\
        </requires>

        <xi:include href="rules.xml"/>
    </source>

%(binary_packages)s
    <xi:include href="changelog.xml"/>
</control>
"""

class SourcePackage(BasePackageMixin):

    def __init__(self, filename):
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()

        content = re.sub(r"^\s*\n$", r"\n", content)
        blocks  = re.split(r"\n\n", content)
        dirname = os.path.dirname(filename)

        self.parse_content(blocks.pop(0))

        self.changelog = Changelog(os.path.join(dirname, "changelog"))
        self.patches   = PatchSeries(os.path.join(dirname, "patches", "series"))
        self.version   = self.changelog.releases[0].version
        self.packages  = []

        for entry in blocks:
            bin_pkg = BinaryPackage(entry)

            # throw out udebs and debug packages
            if bin_pkg.fields.get("section", "") == "debian-installer":
                continue
            if re.match(r".*?-(?:udeb|dbg|debug)$",
                    bin_pkg.fields.get("package", "")):
                continue
            if bin_pkg.fields.get("xc-package-type", "") == "udeb":
                continue

            bin_pkg.load_content_spec(dirname)
            self.packages.append(bin_pkg)
        #end for

        self.arch_indep = True
        for bin_pkg in self.packages:
            if bin_pkg.fields.get("architecture", "all") != "all":
                self.arch_indep = False
                break
            #end if
        #end for
    #end function

    def as_xml(self, indent=0):
        binary_pkgs = ""
        for pkg in self.packages:
            binary_pkgs += "    " + "<xi:include href=\"%s.xml\"/>\n" \
                    % pkg.get("name")
        #end for

        build_deps = ""
        for dep in self.get("build-depends"):
            if dep[1]:
                build_deps += " " * 12
                build_deps += "<package name=\"%s\" version=\"%s\"/>\n" \
                        % (dep[0], dep[1])
            else:
                build_deps += " " * 12 + "<package name=\"%s\"/>\n" % dep[0]
        #end for

        desc = self.packages[0].get("description", "")
        if desc:
            desc = re.sub(r"^\s*", r" " * 12, desc, flags=re.M)

        info_set = {
            "source_name": self.get("name"),
            "arch_indep": "true" if self.arch_indep else "false",
            "summary": self.packages[0].get("summary", ""),
            "description": desc,
            "upstream_version": self.version,
            "build_deps": build_deps,
            "binary_packages": binary_pkgs,
            "patches": self.patches.as_xml(indent=2)
        }

        return SOURCE_PKG_XML_TEMPLATE % info_set
    #end function

    def to_bolt(self):
        with open("changelog.xml", "w+", encoding="utf-8") as f:
            f.write(self.changelog.as_xml())
        with open("rules.xml", "w+", encoding="utf-8") as f:
            f.write(PKG_RULES_XML_TEMPLATE)
        with open("package.xml", "w+", encoding="utf-8") as f:
            f.write(self.as_xml())

        source_section = self.get("section", "unknown")

        for pkg in self.packages:
            if not pkg.get("section", ""):
                pkg.fields["section"] = source_section
            with open(pkg.get("name") + ".xml", "w+", encoding="utf-8") as f:
                f.write(pkg.as_xml())
        #end for
    #end function

#end class
