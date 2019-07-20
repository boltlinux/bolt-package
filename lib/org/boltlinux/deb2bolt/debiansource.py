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
import stat
import shutil
import logging
import subprocess

from org.boltlinux.toolbox.downloader import Downloader
from org.boltlinux.toolbox.libarchive import ArchiveFileReader
from org.boltlinux.deb2bolt.quiltpatchseries import QuiltPatchSeries
from org.boltlinux.deb2bolt.packageutils import PackageUtilsMixin
from org.boltlinux.deb2bolt.debianpackage import DebianPackage
from org.boltlinux.deb2bolt.changelog import Changelog
from org.boltlinux.error import BoltError

from org.boltlinux.package.debianpackagemetadata import (
    DebianPackageVersion, DebianPackageMetaData
)

LOGGER = logging.getLogger(__name__)

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
{sources}
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

class DebianSource(PackageUtilsMixin):

    def __init__(self, pkg_cache, pkg_name, version=None, suite="stable",
            arch="amd64", work_dir="."):
        """
        Relies on a pre-initialized DebianPackageCache instance being passed
        in as the first parameter.

        Initializes a DebianSource instance, where pkg_name is the name of a
        source package in the Debian archive and suite specifies the Debian
        release name (e.g. "stretch").

        If version is not specified, the latest available version will be
        selected.
        """
        self.name     = pkg_name
        self.version  = DebianPackageVersion(version) if version else None
        self.suite    = suite
        self.arch     = arch
        self.files    = {}
        self.patches  = None
        self.packages = []
        self.work_dir = os.path.abspath(work_dir)
        self._cache   = pkg_cache

        try:
            if self.version:
                self.metadata = self._cache.source[self.name][self.version]
            else:
                self.version, self.metadata = \
                    max(self._cache.source[self.name].items())
        except KeyError:
            raise BoltError(
                "Package '{}' version '{}' not found in cache."
                    .format(self.name, self.version or "latest")
            )
        #end try

        for line in self.metadata.get("Checksums-Sha256", "").splitlines():
            sha256sum, size, filename = line\
                .strip()\
                .split()
            self.files[filename] = (sha256sum, size)
        #end for
    #end function

    def download(self):
        """
        Downloads all components of this source package to self.work_dir.
        """
        downloader = Downloader()
        pool_dir   = self.metadata.get("Directory")

        orig_tarball, \
        orig_components, \
        deb_tarball, \
        deb_patches, \
        debdiff_gz = self._guess_file_components()

        files_to_download = [
            orig_tarball,
            deb_tarball,
            debdiff_gz
        ] + orig_components

        for filename in files_to_download:
            if not filename:
                continue

            outfile = os.path.join(self.work_dir, filename)

            url = "/".join([
                self.metadata.base_url,
                pool_dir,
                filename
            ])

            with open(outfile, "wb+") as f:
                LOGGER.info("Fetching {}".format(url))
                for chunk in downloader.get(url):
                    f.write(chunk)
            #end with
        #end for

        return self
    #end function

    def unpack(self):
        """
        Unpacks the components that make up this source package in the right
        order. Does not apply Quilt patches. This method expects to find the
        downloaded files in self.work_dir and unpacks them in place.
        """
        # Unpack orig tarball

        orig_tarball, \
        orig_components, \
        deb_tarball, \
        deb_patches, \
        debdiff_gz = self._guess_file_components()

        pkg_name, pkg_version, _ = \
            self._orig_tarball_split_name(orig_tarball)

        archive_source_path = os.path.join(self.work_dir, orig_tarball)

        outdir = os.path.join(
            self.work_dir,
            "{}-{}".format(pkg_name, pkg_version)
        )
        os.makedirs(outdir, exist_ok=True)

        LOGGER.info("Unpacking Debian package sources to {}".format(outdir))

        with ArchiveFileReader(archive_source_path) as archive:
            archive.unpack_to_disk(outdir, strip_components=1)

        # Unpack orig components

        for comp_filename in orig_components:
            comp_name = self._comp_name_from_comp_filename(comp_filename)
            archive_source_path = os.path.join(self.work_dir, comp_filename)
            comp_dir = os.path.join(outdir, comp_name)
            os.makedirs(comp_dir, exist_ok=True)

            with ArchiveFileReader(archive_source_path) as archive:
                archive.unpack_to_disk(comp_dir, strip_components=1)
        #end for

        # Unpack debdiff.gz

        if debdiff_gz:
            archive_source_path = os.path.join(self.work_dir, debdiff_gz)
            debian_dir = os.path.join(outdir, "debian")
            os.makedirs(debian_dir, exist_ok=True)

            patch_cmd = ["patch", "-d", outdir, "-p1", "-st"]

            with ArchiveFileReader(archive_source_path, raw=True) as archive:
                try:
                    next(iter(archive))
                    proc = subprocess.Popen(patch_cmd, stdin=subprocess.PIPE)
                    for chunk in iter(lambda: archive.read_data(4096), b""):
                        proc.stdin.write(chunk)
                    proc.stdin.close()
                    proc.wait()
                except StopIteration:
                    pass
            #end with
        #end if

        # Unpack Debian changes tarball

        if deb_tarball:
            archive_source_path = os.path.join(self.work_dir, deb_tarball)

            with ArchiveFileReader(archive_source_path) as archive:
                archive.unpack_to_disk(outdir)
        #end if

        return self
    #end function

    def run_rules(self, run_rules=None):
        """
        For each target in run_rules, invokes `fakeroot debian/rules <target>`.
        """
        if not run_rules:
            return

        orig_tarball, \
        orig_components, \
        deb_tarball, \
        deb_patches, \
        debdiff_gz = self._guess_file_components()

        pkg_name, pkg_version, _ = \
            self._orig_tarball_split_name(orig_tarball)

        deb_source_dir = os.path.join(
            self.work_dir,
            "{}-{}".format(pkg_name, pkg_version)
        )

        for target in run_rules:
            LOGGER.info("Invoking debian/rules target {}".format(target))

            cmd = ["fakeroot", "make", "-C", deb_source_dir, "-f",
                    "debian/rules", target]
            subprocess.run(cmd)
        #end for
    #end function

    def copy_sources_and_patches(self, target_dir):
        """
        Copies the original sources, debdiff and any patches from
        self.work_dir to target_dir. Below target_dir the assets are placed
        into subfolder <pkg_name>/<pkg_version>.
        """
        orig_tarball, \
        orig_components, \
        deb_tarball, \
        deb_patches, \
        debdiff_gz = self._guess_file_components()

        pkg_name, pkg_version, _ = \
            self._orig_tarball_split_name(orig_tarball)

        unpacked_source_dir = os.path.join(
            self.work_dir,
            "{}-{}".format(pkg_name, pkg_version)
        )

        outdir = os.path.abspath(
            os.path.join(target_dir, pkg_name, pkg_version)
        )
        os.makedirs(outdir, exist_ok=True)

        LOGGER.info("Copying sources and patches to {}".format(outdir))

        # Copy orig tarball

        archive_source_path = os.path.join(self.work_dir, orig_tarball)
        archive_target_path = \
            os.path.join(outdir, self._orig_tarball_dist_name(orig_tarball))
        shutil.copy2(archive_source_path, archive_target_path)

        # Copy any orig components

        for comp in orig_components:
            archive_source_path = os.path.join(self.work_dir, comp)
            archive_target_path = \
                os.path.join(outdir, self._orig_tarball_dist_name(comp))
            shutil.copy2(archive_source_path, archive_target_path)
        #end for

        # Copy debdiff

        if debdiff_gz:
            archive_source_path = os.path.join(self.work_dir, debdiff_gz)
            archive_target_path = \
                os.path.join(outdir, self._debdiff_dist_name(debdiff_gz))
            shutil.copy2(archive_source_path, archive_target_path)
        #end if

        # Collect patches

        for patch_subdir in ["patches-applied", "patches"]:
            series_file = os.path.join(unpacked_source_dir,
                "debian", patch_subdir, "series")

            if not os.path.isfile(series_file):
                continue

            tarfile = "debian-patches-{}.tar.gz"\
                .format(self.version.revision)

            patches = QuiltPatchSeries(series_file)
            if not patches:
                continue

            self.patches = patches
            self.files[tarfile] = \
                self.patches.create_tarball(os.path.join(outdir, tarfile))

            break
        #end for

        return self
    #end function

    def parse_control_file(self):
        """
        Parses the control file and creates a list of DebianBinaryPackages
        instances stored in self.packages.
        """
        orig_tarball, \
        orig_components, \
        deb_tarball, \
        deb_patches, \
        debdiff_gz = self._guess_file_components()

        pkg_name, pkg_version, _ = \
            self._orig_tarball_split_name(orig_tarball)

        unpacked_source_dir = os.path.join(
            self.work_dir,
            "{}-{}".format(pkg_name, pkg_version)
        )

        debian_control_file = \
            os.path.join(unpacked_source_dir, "debian", "control")

        LOGGER.info("Parsing metadata from {}".format(debian_control_file))

        with open(debian_control_file, "r", encoding="utf-8") as f:
            content = f.read()

        content = content.strip()
        content = re.sub(r"^\s*\n$", r"\n", content, flags=re.M)
        blocks  = re.split(r"\n\n+", content)

        while True:
            source_meta = DebianPackageMetaData(string=blocks.pop(0))
            if source_meta:
                break
        #end while

        for i in range(0, len(blocks)):
            metadata = DebianPackageMetaData(string=blocks[i])

            if not metadata:
                continue

            architecture = metadata.get("Architecture", "any")
            if architecture not in ["all", "any"]:
                arch_list = architecture.split()
                if self.arch not in arch_list:
                    continue
            #end if

            package = metadata["Package"]
            if package.endswith("-dbg"):
                continue

            pkg = DebianPackage(
                self._cache,
                metadata["Package"],
                version=self.version.full,
                suite=self.suite,
                arch=self.arch,
                work_dir=self.work_dir
            )

            pkg.metadata["Description"] = metadata.get("Description", "")
            pkg.metadata["Section"] = metadata.get(
                "Section",
                source_meta["Section"]
            )

            self.packages.append(pkg)
        #end for
    #end function

    def build_content_spec(self):
        for pkg in self.packages:
            pkg.build_content_spec()

        self._simplify_package_contents()
    #end function

    def to_bolt(self, target_dir, maintainer_info=None):
        orig_tarball, \
        orig_components, \
        deb_tarball, \
        deb_patches, \
        debdiff_gz = self._guess_file_components()

        pkg_name, pkg_version, _ = \
            self._orig_tarball_split_name(orig_tarball)

        unpacked_source_dir = os.path.join(
            self.work_dir,
            "{}-{}".format(pkg_name, pkg_version)
        )

        # Changelog

        debian_changelog_file = \
            os.path.join(unpacked_source_dir, "debian", "changelog")
        changelog = Changelog(debian_changelog_file)

        outfile = os.path.join(target_dir, "changelog.xml")
        with open(outfile, "w+", encoding="utf-8") as f:
            f.write(changelog.to_xml(maintainer_info=maintainer_info))

        # Binary packages

        for pkg in self.packages:
            outfile = os.path.join(target_dir, "{}.xml".format(pkg.name))
            with open(outfile, "w+", encoding="utf-8") as f:
                f.write(pkg.to_xml())
        #end for

        # Build rules

        outfile = os.path.join(target_dir, "rules.xml")
        with open(outfile, "w+", encoding="utf-8") as f:
            f.write(PKG_RULES_XML_TEMPLATE)

        # source package

        outfile = os.path.join(target_dir, "package.xml")
        with open(outfile, "w+", encoding="utf-8") as f:
            f.write(self._to_xml(
                orig_tarball,
                orig_components,
                deb_tarball,
                deb_patches,
                debdiff_gz)
            )
        #end with
    #end function

    # PRIVATE

    def _to_xml(self, orig_tarball, orig_components, deb_tarball, deb_patches,
            debdiff_gz):
        """Renders the source package (and binary packages) to a complete
        build XML."""
        metadata = self.metadata.to_bolt()

        binary_pkgs = ""
        for pkg in self.packages:
            binary_pkgs += \
                '    <xi:include href="{}.xml"/>\n'.format(pkg.name)

        build_deps = ""
        for dep_name, dep_version in metadata["Build-Depends"]:
            if self.is_pkg_name_debian_specific(dep_name):
                continue
            if self.is_pkg_name_implicit(dep_name):
                continue

            build_deps += ' ' * 12

            if dep_version:
                build_deps += \
                    '<package name="{}" version="{}"/>\n'\
                    .format(dep_name, dep_version)
            else:
                build_deps += \
                    '<package name="{}"/>\n'\
                    .format(dep_name)
            #end if
        #end for

        build_deps = build_deps.strip('\n')
        pkg_0_meta = self.packages[0].metadata.to_bolt()

        description = pkg_0_meta.get("Description", "")
        if description:
            description = re.sub(r"^\s*", r" " * 12, description, flags=re.M)

        sources = self._sources_xml_part(
            orig_tarball,
            orig_components,
            deb_tarball,
            deb_patches,
            debdiff_gz
        )

        patches = self.patches.as_xml(indent=2) if self.patches else ""

        context = {
            "source_name":       self.name,
            "upstream_version":  self.version,
            "summary":           pkg_0_meta.get("Summary", ""),
            "description":       description,
            "arch_indep":        "true" if self._is_arch_indep() else "false",
            "patches":           patches,
            "sources":           sources,
            "build_deps":        build_deps,
            "binary_packages":   binary_pkgs,
        }

        return SOURCE_PKG_XML_TEMPLATE.format(**context)
    #end function

    def _sources_xml_part(self, orig_tarball, orig_components, deb_tarball,
            deb_patches, debdiff_gz):
        template = '<file src="{tarball}" subdir="{subdir}"\n' \
            '    sha256sum="{sha256sum}"/>'

        sources = []

        sources.append(template.format(
            tarball=self._orig_tarball_dist_name(orig_tarball),
            subdir="sources",
            sha256sum=self.files[orig_tarball][0]
        ))

        for comp_filename in orig_components:
            comp_name = self._comp_name_from_comp_filename(comp_filename)

            sources.append(template.format(
                tarball=self._orig_tarball_dist_name(comp_filename),
                subdir=os.sep.join(["sources", comp_name]),
                sha256sum=self.files[comp_filename][0]
            ))
        #end for

        if deb_patches:
            sources.append(template.format(
                tarball=deb_patches,
                subdir="patches",
                sha256sum=self.files[deb_patches][0]
            ))
        #end if

        if debdiff_gz:
            sources.append(template.format(
                tarball=self._debdiff_dist_name(debdiff_gz),
                subdir="patches",
                sha256sum=self.files[debdiff_gz][0]
            ))
        #end if

        return re.sub(r"^", r" " * 12, "\n".join(sources), flags=re.M)
    #end function

    def _comp_name_from_comp_filename(self, comp_filename):
        m = re.search(
            r"\.orig-(?P<comp_name>[^.]+)\.tar\.(?:gz|bz2|xz)$",
            comp_filename
        )

        return m.group("comp_name")
    #end function

    def _is_arch_indep(self):
        for pkg in self.packages:
            if pkg.metadata.get("Architecture", "all") != "all":
                return False
        #end for

        return True
    #end function

    def _debdiff_dist_name(self, debdiff_gz):
        """
        Parses the debdiff filename and converts e.g. alevt_1.6.2-5.1.diff.gz
        to alevt-1.6.2-5.1.debdiff.gz.
        """
        return debdiff_gz \
            .replace("_", "-") \
            .replace(".diff.", ".debdiff.")
    #end function

    def _orig_tarball_dist_name(self, orig_tarball):
        """
        Parses the orig tarball and converts e.g. bison_1.2.0.orig.tar.gz to
        bison-1.2.0.tar.gz.
        """
        pkg_name, pkg_version, pkg_ext = \
            self._orig_tarball_split_name(orig_tarball)

        return "{}-{}{}".format(pkg_name, pkg_version, pkg_ext)
    #end function

    def _orig_tarball_split_name(self, orig_tarball):
        """
        Parses the orig tarball name into pkg_name, pkg_version and pkg_ext,
        for example ("bison", "1.0", ".tar.bz2").
        """
        m = re.match(
            r"^(?P<pkg_name>[^_]+)_"
            r"(?P<pkg_version>.*?)"
            r"(:?\.orig(?:-(?P<orig_name>[^.]+))?)?"
            r"(?P<pkg_ext>\.tar\.(?:gz|bz2|xz))$",
            orig_tarball
        )

        if not m.group("orig_name"):
            pkg_name = m.group("pkg_name")
        else:
            pkg_name = "{}-{}".format(
                m.group("pkg_name"), m.group("orig_name")
            )
        #end if

        return pkg_name, m.group("pkg_version"), m.group("pkg_ext")
    #end function

    def _guess_file_components(self):
        """
        Guesses available component types and return a tuple

        (orig_tarball, orig_components, deb_tarball, debdiff_gz)

        all of which are strings, except for orig_components, which is a list
        of strings.
        """
        orig_tarball    = None
        orig_components = []
        deb_tarball     = None
        deb_patches     = None
        debdiff_gz      = None

        for filename in self.files:
            # Format 3.0 additional component for original sources:
            if re.search(r"\.orig-[^.]+\.tar\.(?:gz|bz2|xz)$", filename):
                orig_components.append(filename)
            # Format 1.0 Debian diff.gz:
            elif re.search(r"\.diff\.(?:gz|bz2|xz)$", filename):
                debdiff_gz = filename
            # Generic match for an orig tarball (Format 1.0 or 3.0):
            elif re.search(r"\.orig\.tar\.(?:gz|bz2|xz)$", filename):
                orig_tarball = filename
            # Format 3.0 tarball with Debian-specific changes:
            elif re.search(r"\.debian\.tar.(?:gz|bz2|xz)$", filename):
                deb_tarball = filename
            # Special case collected debian-patches tarball:
            elif re.search(r"^debian-patches-.*?\.tar\.(?:gz|bz2|xz)$",
                    filename):
                deb_patches = filename
            # Special case Debian native package source tarball:
            elif re.search(r"\.tar\.(?:gz|bz2|xz)$", filename):
                if not filename.startswith("debian-patches-"):
                    orig_tarball = filename
            else:
                continue
        #end for

        return orig_tarball, orig_components, deb_tarball, \
                deb_patches, debdiff_gz
    #end function

    def _simplify_package_contents(self):
        """
        Reduce the content listing of all binary packages to the minimum amount
        of entries needed to represent the file sets to be included in each
        package.
        """
        for pkg in self.packages:
            uniq_prefixes = {}
            pkg.contents.sort()

            for entry in pkg.contents:
                entry_path = os.path.dirname(entry[0])
                entry_type = entry[1]
                entry_uniq = True

                if not entry_path or stat.S_ISDIR(entry_type) != 0:
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

                if stat.S_ISDIR(entry_type) != 0:
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

#end class
