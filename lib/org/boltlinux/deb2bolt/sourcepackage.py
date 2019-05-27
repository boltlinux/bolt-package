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
import pwd
import stat
import shutil
import socket

import org.boltlinux.package.libarchive as libarchive

from org.boltlinux.toolbox import file_sha256sum
from org.boltlinux.package.libarchive import ArchiveEntry, ArchiveFileWriter
from org.boltlinux.deb2bolt.debianpackagecache import DebianPackageCache
from org.boltlinux.deb2bolt.changelog import Changelog
from org.boltlinux.deb2bolt.patchseries import PatchSeries
from org.boltlinux.deb2bolt.binarypackage import BinaryPackage
from org.boltlinux.deb2bolt.basepackage import BasePackage
from org.boltlinux.deb2bolt.packageutils import PackageUtilsMixin
from org.boltlinux.error import BoltSyntaxError, InvocationError

PKG_RULES_XML_TEMPLATE = """\
<?xml version="1.0" encoding="utf-8"?>
<rules>
    <prepare>
    <![CDATA[

cd "$BOLT_BUILD_DIR"
"$BOLT_SOURCE_DIR/configure" \\
    --prefix="$BOLT_INSTALL_PREFIX" \\
    --build="$BOLT_HOST_TYPE" \\
    --host="$BOLT_HOST_TYPE" \\
    --disable-nls

    ]]>
    </prepare>

    <build>
    <![CDATA[

cd "$BOLT_BUILD_DIR"
make -j"$BOLT_PARALLEL_JOBS"

    ]]>
    </build>

    <install>
    <![CDATA[

cd "$BOLT_BUILD_DIR"
make DESTDIR="$BOLT_INSTALL_DIR" install

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

    <source name="{source_name}" architecture-independent="{arch_indep}">
        <description>
            <summary>{summary}</summary>
            <p>
{description}
            </p>
        </description>

        <sources>
            <file src="{sources_tarball}" subdir="sources"
                sha256sum="{sources_sha256sum}"/>
            <file src="{patches_tarball}" subdir="patches"
                sha256sum="{patches_sha256sum}"/>
        </sources>

{patches}

        <requires>
{build_deps}
        </requires>

        <xi:include href="rules.xml"/>
    </source>

{binary_packages}
    <xi:include href="changelog.xml"/>
</control>
"""

class SourcePackage(BasePackage, PackageUtilsMixin):

    def __init__(self, control_file, app_config, suite="stable"):
        super().__init__()

        if not os.path.exists(control_file):
            raise InvocationError("no such file '%s'." % control_file)
        with open(control_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.sources_tarball = ""
        self.sources_tarball_sha256sum = ""
        self.patches_tarball = ""
        self.patches_tarball_sha256sum = ""
        self.patches = PatchSeries()

        ######################################################################
        # Generate maintainer info.

        pwent            = pwd.getpwuid(os.getuid())
        maintainer_name  = pwent.pw_gecos.split(",")[0] or "Unknown User"
        maintainer_email = pwent.pw_name + "@" + socket.gethostname()
        maintainer_info  = app_config.get("maintainer-info", {})

        maintainer_info.setdefault("name",  maintainer_name)
        maintainer_info.setdefault("email", maintainer_email)

        ######################################################################
        # Sanitize contents, split and parse first block.

        content = re.sub(r"^\s*\n$", r"\n", content, flags=re.M)
        blocks  = re.split(r"\n\n", content)

        try:
            self.parse_content(blocks.pop(0))
        except:
            raise BoltSyntaxError("error parsing control file.")

        self.debian_directory = os.path.dirname(control_file)

        ######################################################################
        # Read changelog and retrieve version information.

        self.changelog = Changelog(
            os.path.join(self.debian_directory, "changelog"),
            maintainer_info
        )

        latest_release = self.changelog.releases[0]

        self.version = latest_release.version
        self.revision = latest_release.revision

        ######################################################################
        # Open and refresh the package cache.

        pkg_cache = DebianPackageCache(suite)
        pkg_cache.update(what=DebianPackageCache.BINARY)

        ######################################################################
        # Parse remaining blocks as binary packages.

        self.packages = []

        for entry in blocks:
            if not entry.strip():
                continue

            bin_pkg = BinaryPackage(entry)

            if not "name" in bin_pkg.fields:
                continue

            bin_pkg.fields["version"] = self.version

            # throw out udebs and debug packages
            if bin_pkg.fields.get("section", "") == "debian-installer":
                continue
            if re.match(r".*?-(?:udeb|dbg|debug)$",
                    bin_pkg.fields.get("package", "")):
                continue
            if bin_pkg.fields.get("xc-package-type", "") == "udeb":
                continue

            bin_pkg.generate_content_spec(
                bin_pkg.get("name"),
                latest_release.upstream_version,
                pkg_cache
            )

            self.packages.append(bin_pkg)
        #end for

        ######################################################################
        # Determine if package is architecture independent.

        self.arch_indep = True
        for bin_pkg in self.packages:
            if bin_pkg.fields.get("architecture", "all") != "all":
                self.arch_indep = False
                break
            #end if
        #end for

        self._simplify_package_contents()
    #end function

    def to_bolt(self, set_maintainer=False, **kwargs):
        """Analyzes Debian sources and produces an equivalent (as far as
        possible) Bolt OS sources package."""

        ######################################################################
        # Look for original tarball.

        debian_artifact_dir = os.path.normpath(
            os.path.join(self.debian_directory, "..", "..")
        )

        self.sources_tarball, self.sources_tarball_sha256sum = \
            self._copy_orig_tarball(
                debian_artifact_dir,
                os.path.abspath(self.version),
                self.version
            )

        ######################################################################
        # Look for patches.

        self.patches, self.patches_tarball, self.patches_tarball_sha256sum = \
            self._generate_patch_tarball(
                self.debian_directory,
                os.path.abspath(self.version),
                self.revision
            )

        ######################################################################
        # Produce changelog.xml and rules.xml

        with open("changelog.xml", "w+", encoding="utf-8") as f:
            f.write(self.changelog.as_xml(set_maintainer=set_maintainer))
        with open("rules.xml", "w+", encoding="utf-8") as f:
            f.write(PKG_RULES_XML_TEMPLATE)

        ######################################################################
        # Render the binary packages.

        source_section = self.get("section", "unknown")

        for pkg in self.packages:
            pkg_name = pkg.get("name")

            # TODO: filter these out earlier.
            if pkg_name.endswith("-doc"):
                continue

            if not pkg.get("section"):
                pkg.fields["section"] = source_section

            with open(pkg_name + ".xml", "w+", encoding="utf-8") as f:
                f.write(pkg.as_xml())
        #end for

        ######################################################################
        # Render the main package.xml file.

        with open("package.xml", "w+", encoding="utf-8") as f:
            f.write(self._as_xml())
    #end function

    # PRIVATE

    def _as_xml(self, indent=0):
        """Renders the source package (and binary packages) to a complete
        build XML."""
        ######################################################################
        # Generate xincludes for binary packages.

        binary_pkgs = ""
        for pkg in self.packages:
            pkg_name = pkg.get("name")
            if pkg_name.endswith("-doc"):
                continue
            binary_pkgs += \
                '    <xi:include href="{}.xml"/>\n'.format(pkg_name)
        #end for

        ######################################################################
        # Generate list of build dependencies.

        build_deps = ""

        for dependency in self.get("build-depends"):
            pkg_name, pkg_version = dependency

            if self.is_pkg_name_debian_specific(pkg_name):
                continue

            if pkg_version:
                build_deps += ' ' * 12
                build_deps += '<package name="{}" version="{}"/>\n'\
                                .format(pkg_name, pkg_version)
            else:
                build_deps += ' ' * 12
                build_deps += '<package name="{}"/>\n'\
                                .format(pkg_name)
        #end for

        build_deps = build_deps.strip('\n')

        ######################################################################
        # Use first binary packages' description for source package.

        description = self.packages[0].get("description", "")
        if description:
            description = re.sub(r"^\s*", r" " * 12, description, flags=re.M)

        ######################################################################
        # Render the template.

        context = {
            "source_name":       self.get("name"),
            "upstream_version":  self.version,
            "summary":           self.packages[0].get("summary", ""),
            "description":       description,
            "arch_indep":        "true" if self.arch_indep else "false",
            "patches":           self.patches.as_xml(indent=2),
            "sources_tarball":   self.sources_tarball,
            "sources_sha256sum": self.sources_tarball_sha256sum,
            "patches_tarball":   self.patches_tarball,
            "patches_sha256sum": self.patches_tarball_sha256sum,
            "build_deps":        build_deps,
            "binary_packages":   binary_pkgs,
        }

        return SOURCE_PKG_XML_TEMPLATE.format(**context)
    #end function

    def _simplify_package_contents(self):
        """
        Reduce the content listing to the minimum amount of entries neeeded to
        package up all files in the listing.
        """
        for pkg in self.packages:
            uniq_prefixes = {}
            pkg.contents.sort()

            for entry in pkg.contents:
                entry_path = os.path.dirname(entry[0])
                entry_type = entry[1]
                entry_uniq = True

                if not entry_path or entry_type == stat.S_IFDIR:
                    continue

                entry_path = entry_path.rstrip(os.sep) + os.sep

                # check if the path is also in another package
                for tmp_pkg in self.packages:
                    if id(tmp_pkg) == id(pkg):
                        continue
                    for tmp_entry in tmp_pkg.contents:
                        tmp_entry_path = tmp_entry[0]
                        if tmp_entry_path.startswith(entry_path):
                            entry_uniq = False
                            break
                    #end for
                    if not entry_uniq:
                        break
                #end for

                if not entry_uniq:
                    continue

                # check if there are collisions and fix them
                for prefix in list(uniq_prefixes):
                    if prefix.startswith(entry_path):
                        del uniq_prefixes[prefix]
                    elif entry_path.startswith(prefix + os.sep):
                        entry_uniq = False
                        break
                    #end if
                #end for

                if entry_uniq:
                    uniq_prefixes[entry_path.rstrip(os.sep)] = 1
            #end for

            # delete entries that are included in a prefix
            i = 0
            while i < len(pkg.contents):
                entry = pkg.contents[i]

                entry_path = entry[0]
                entry_type = entry[1]

                if entry_type != stat.S_IFDIR:
                    entry_path = os.path.dirname(entry_path)

                index_deleted = False

                for prefix in uniq_prefixes:
                    if entry_path == prefix or \
                            entry_path.startswith(prefix + os.sep):
                        del pkg.contents[i]
                        index_deleted = True
                        break
                    #end if
                #end for

                if not index_deleted:
                    i += 1
            #end while

            for entry_path in uniq_prefixes:
                pkg.contents.append([entry_path, 0, 0, "root", "root"])
        #end for
    #end function

    def _copy_orig_tarball(self, in_dir, out_dir, pkg_version):
        """Looks for the orig tarball and copies it to a new name according to
        Bolt OS conventions."""
        orig_tarball = None

        ######################################################################
        # Find the orig tarball.

        for entry in os.listdir(in_dir):
            m = re.match(
                r"^%s_.*?\.orig\.tar.[a-z0-9]+$" % self.get("name"),
                entry
            )
            if m:
                orig_tarball = entry
                break
        #end for

        if not orig_tarball:
            return ("", "")

        ######################################################################
        # Rename it...

        extension = \
            orig_tarball.rsplit(".", 1)[-1]
        copy_tarball = \
            "{}-{}.tar.{}".format(self.get("name"), pkg_version, extension)

        orig_tarball_abs_path = os.path.join(in_dir, orig_tarball)
        copy_tarball_abs_path = os.path.join(out_dir, copy_tarball)

        ######################################################################
        # ...and copy it.

        os.makedirs(out_dir, exist_ok=True)

        shutil.copyfile(
            orig_tarball_abs_path,
            copy_tarball_abs_path
        )

        return copy_tarball, file_sha256sum(copy_tarball_abs_path)
    #end function

    def _generate_patch_tarball(self, in_dir, out_dir, pkg_revision):
        """Looks for patches and generates a patch tarball according to Bolt
        OS conventions."""
        patches = PatchSeries(os.sep.join(["patches", "series"]))

        ######################################################################
        # Search for patches.

        for patch_subdir in ["patches-applied", "patches"]:
            series_file = os.path.join(in_dir, patch_subdir, "series")

            if os.path.exists(series_file):
                patches = PatchSeries(series_file)
                break
            #end if
        #end for

        if not patches:
            return ("", "")

        ######################################################################
        # Prepare to re-package patches.

        os.makedirs(out_dir, exist_ok=True)

        tarball = "debian.{}.tar.gz".format(pkg_revision)
        tarball_abs_path = os.path.join(out_dir, tarball)

        patch_dir = os.path.join(in_dir, patch_subdir)

        ######################################################################
        # Write the new patch tarball.

        with ArchiveFileWriter(tarball_abs_path, libarchive.FORMAT_TAR_USTAR,
                libarchive.COMPRESSION_GZIP) as archive:
            with ArchiveEntry() as archive_entry:
                for p in patches:
                    # Remove extra parameter, e.g. -p1
                    p = re.sub(r"\s+-p\d+\s*$", r"", p)

                    patch_abs_path = os.path.join(patch_dir, p)

                    archive_entry.clear()
                    archive_entry.copy_stat(patch_abs_path)
                    archive_entry.pathname = os.path.join("patches", p)
                    archive_entry.uname = "root"
                    archive_entry.gname = "root"
                    archive.write_entry(archive_entry)

                    with open(patch_abs_path, "rb") as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            archive.write_data(chunk)
                    #end with
                #end for
            #end with
        #end with

        return patches, tarball, file_sha256sum(tarball_abs_path)
    #end function

#end class
