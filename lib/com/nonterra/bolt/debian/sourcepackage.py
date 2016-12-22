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
import hashlib
import shutil
import com.nonterra.bolt.package.libarchive as libarchive
from com.nonterra.bolt.package.libarchive import ArchiveEntry, ArchiveFileWriter
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
            <file src="%(tarball)s" subdir="sources"
                sha256sum="%(source_sha256sum)s"/>
            <file src="patches.01.tar.gz" subdir="patches"
                sha256sum="%(patches_sha256sum)s"/>
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
        self.revision  = self.changelog.releases[0].revision
        self.packages  = []
        self.directory = dirname
        self.tarball   = self.find_orig_tarball(dirname)

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

        if self.tarball:
            h = hashlib.sha256()
            with open(self.tarball, "rb") as f:
                while True:
                    buf = f.read(4096)
                    if not buf:
                        break
                    h.update(buf)
                #end while
            #end with
            self.sha256sum = h.hexdigest()
        else:
            self.sha256sum = ""
        #end if

        self.sha256sum_patches = ""
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

        if self.tarball:
            extension = self.tarball.rsplit(".", 1)[-1]
            tarball   = self.get("name") + "-" + self.version + ".tar." + \
                    extension
        else:
            tarball = self.get("name") + "-" + self.version + ".tar.gz"
        #end if

        info_set = {
            "source_name": self.get("name"),
            "arch_indep": "true" if self.arch_indep else "false",
            "summary": self.packages[0].get("summary", ""),
            "description": desc,
            "upstream_version": self.version,
            "tarball": tarball,
            "build_deps": build_deps,
            "binary_packages": binary_pkgs,
            "patches": self.patches.as_xml(indent=2),
            "source_sha256sum": self.sha256sum,
            "patches_sha256sum": self.sha256sum_patches
        }

        return SOURCE_PKG_XML_TEMPLATE % info_set
    #end function

    def find_orig_tarball(self, directory):
        search_dir  = os.path.join(directory, "..", "..")
        source_name = self.get("name")

        for entry in os.listdir(search_dir):
            m = re.match("^%s_.*?\\.orig\\.tar\\.\\w+$" % source_name, entry)
            if m:
                return os.path.join(search_dir, entry)
        #end for

        return None
    #end function

    def to_bolt(self, gen_patches=False, use_orig=False):
        with open("changelog.xml", "w+", encoding="utf-8") as f:
            f.write(self.changelog.as_xml())
        with open("rules.xml", "w+", encoding="utf-8") as f:
            f.write(PKG_RULES_XML_TEMPLATE)

        source_section = self.get("section", "unknown")

        for pkg in self.packages:
            if not pkg.get("section", ""):
                pkg.fields["section"] = source_section
            with open(pkg.get("name") + ".xml", "w+", encoding="utf-8") as f:
                f.write(pkg.as_xml())
        #end for

        if gen_patches:
            patch_dir = self.directory + os.sep + "patches"
            filename  = self.version + os.sep + "patch.%s.tar.gz" \
                    % self.revision.zfill(2)
            os.makedirs(self.version, exist_ok=True)

            with ArchiveFileWriter(filename, libarchive.FORMAT_TAR_USTAR,
                    libarchive.COMPRESSION_GZIP) as archive:
                with ArchiveEntry() as archive_entry:
                    for p in self.patches:
                        abs_path = os.path.join(patch_dir, p)

                        archive_entry.clear()
                        archive_entry.copy_stat(abs_path)
                        archive_entry.pathname = "patches" + os.sep + p
                        archive_entry.uname = "root"
                        archive_entry.gname = "root"
                        archive.write_entry(archive_entry)

                        with open(filename, "rb") as f:
                            while True:
                                buf = f.read(4096)
                                if not buf:
                                    break
                                archive.write_data(buf)
                            #end while
                        #end with
                    #end for
                #end with
            #end with

            with open(filename, "rb") as f:
                h = hashlib.sha256()
                while True:
                    buf = f.read(4096)
                    if not buf:
                        break
                    h.update(buf)
                #end while
                self.sha256sum_patches = h.hexdigest()
            #end with
        #end if

        if use_orig and self.tarball:
            extension = self.tarball.rsplit(".", 1)[-1]
            filename  = self.get("name") + "-" + self.version + ".tar." + \
                    extension
            os.makedirs(self.version, exist_ok=True)
            shutil.copyfile(self.tarball, self.version + os.sep +filename)
        #end if

        with open("package.xml", "w+", encoding="utf-8") as f:
            f.write(self.as_xml())
    #end function

#end class
