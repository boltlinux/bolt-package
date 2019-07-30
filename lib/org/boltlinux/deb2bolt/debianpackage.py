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
import stat
import logging

from tempfile import TemporaryDirectory

from org.boltlinux.toolbox.downloader import Downloader
from org.boltlinux.toolbox.libarchive import ArchiveFileReader
from org.boltlinux.toolbox.progressbar import ProgressBar
from org.boltlinux.package.debianpackagemetadata import DebianPackageVersion
from org.boltlinux.deb2bolt.packageutils import PackageUtilsMixin
from org.boltlinux.error import BoltError

LOGGER = logging.getLogger(__name__)

BINARY_PKG_XML_TEMPLATE = """\
<?xml version="1.0" encoding="utf-8"?>
<package name="{binary_name}" section="{section}">
    <description>
        <summary>{summary}</summary>
        <p>
{description}
        </p>
    </description>

    <requires>
{install_deps}\
    </requires>

    <contents>
{contents}\
    </contents>
</package>
"""

class DebianPackage(PackageUtilsMixin):

    def __init__(self, pkg_cache, pkg_name, version=None, suite="stable",
            arch="amd64", work_dir="."):
        """
        Relies on a pre-initialized DebianPackageCache instance being passed
        in as the first parameter.

        Initializes a DebianPackage instance where pkg_name is the name of
        a Debian binary package in the Debian package archive.

        If version is not specified, the latest available version will be
        selected.
        """
        self.name     = pkg_name
        self.version  = DebianPackageVersion(version) if version else None
        self.suite    = suite
        self.arch     = arch
        self.contents = []
        self.work_dir = os.path.abspath(work_dir)
        self._cache   = pkg_cache

        try:
            if self.version:
                self.metadata = \
                    self._cache.binary[self.name][self.version.full]
            else:
                self.version, self.metadata = \
                    max(self._cache.binary[self.name].items())
        except KeyError:
            raise BoltError(
                "package '{}' version '{}' not found in cache."
                    .format(self.name, self.version or "latest")
            )
        #end try
    #end function

    def build_content_spec(self):
        downloader = Downloader(progress_bar_class=ProgressBar)

        filename = self.metadata["Filename"]
        outfile  = os.path.join(self.work_dir, os.path.basename(filename))
        url      = "/".join([self.metadata.base_url, filename])

        LOGGER.info("fetching {}".format(url))

        with open(outfile, "wb+") as f:
            for chunk in downloader.get(url):
                f.write(chunk)
        #end with

        self.contents = \
            self._binary_deb_list_contents(outfile)
    #end function

    def to_xml(self):
        self.contents.sort()

        metadata     = self.metadata.to_bolt()
        dependencies = metadata.get("Depends", []) + \
            metadata.get("Pre-Depends", [])

        install_deps = ""
        for pkg_name, pkg_version in dependencies:
            if self.is_pkg_name_debian_specific(pkg_name):
                continue

            if pkg_version:
                install_deps += ' ' * 8
                install_deps += '<package name="%s" version="%s"/>\n' \
                        % (pkg_name, pkg_version)
            else:
                install_deps += ' ' * 8
                install_deps += '<package name="%s"/>\n' % pkg_name
        #end for

        contents = ""
        for entry in self.contents:
            (entry_path, entry_type, entry_mode, entry_uname,
                    entry_gname) = entry

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

            contents += ' ' * 8
            contents += '<%s src="%s"' % (
                "dir" if entry_type == stat.S_IFDIR else "file",
                entry_path
            )

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

        context = {
            "binary_name":  self.name,
            "section":      metadata["Section"],
            "summary":      metadata["Summary"],
            "description":  metadata.get("Description", ""),
            "install_deps": install_deps,
            "contents":     contents
        }

        return BINARY_PKG_XML_TEMPLATE.format(**context)
    #end function

    # PRIVATE

    def _binary_deb_list_contents(self, filename):
        contents = []

        LOGGER.info("analyzing contents of {}".format(filename))

        with TemporaryDirectory() as tmpdir:
            contents = self._binary_deb_list_contents_impl(filename, tmpdir)

        return contents
    #end function

    def _binary_deb_list_contents_impl(self, filename, tmpdir):
        data_tarball = None

        with ArchiveFileReader(filename) as archive:
            for entry in archive:
                if entry.pathname.startswith("data.tar"):
                    data_tarball = os.path.join(tmpdir, entry.pathname)

                    with open(data_tarball, "wb+") as f:
                        for chunk in iter(
                                lambda: archive.read_data(4096), b""):
                            f.write(chunk)
                        #end for
                    #end with

                    break
                #end if
            #end for
        #end with

        if not data_tarball:
            raise BoltError("binary package %s contains no data." %
                    data_tarball)

        contents = []

        # parse data file entries and build content listing
        with ArchiveFileReader(data_tarball) as archive:
            for entry in archive:
                entry_path = self.fix_path(entry.pathname)

                if entry.is_directory and self.is_path_implicit(entry_path):
                    continue
                if self.is_doc_path(entry_path):
                    continue
                if self.is_l10n_path(entry_path):
                    continue
                if self.is_menu_path(entry_path):
                    continue

                if entry.is_directory:
                    entry_type = stat.S_IFDIR
                elif entry.is_symbolic_link:
                    entry_type = stat.S_IFLNK
                elif entry.is_file or entry.is_hardlink:
                    entry_type = stat.S_IFREG
                else:
                    raise BoltError(
                        "type of '%s' unknown '%d'" % (entry_path, entry_type)
                    )

                contents.append([
                    entry_path,
                    entry_type,
                    entry.mode,
                    entry.uname,
                    entry.gname
                ])
            #end for
        #end with

        return contents
    #end function

#end class
