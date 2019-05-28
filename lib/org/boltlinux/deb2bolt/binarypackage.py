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
import sys
import logging

import urllib.error
import urllib.request

from tempfile import TemporaryDirectory

from org.boltlinux.error import BoltSyntaxError, NetworkError
from org.boltlinux.package.libarchive import ArchiveEntry, ArchiveFileReader
from org.boltlinux.toolbox.progressbar import ProgressBar
from org.boltlinux.deb2bolt.basepackage import BasePackage
from org.boltlinux.deb2bolt.packageutils import PackageUtilsMixin

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

class BinaryPackage(BasePackage, PackageUtilsMixin):

    def __init__(self, content):
        super().__init__()
        try:
            self.parse_content(content)
        except:
            raise BoltSyntaxError("error parsing control file.")

        self.contents = []
    #end function

    def generate_content_spec(self, pkg_name, pkg_version, pkg_cache):
        try:
            pkg_meta = pkg_cache.binary[pkg_name][pkg_version]
        except KeyError:
            LOGGER.warning(
                "Cannot find Debian package '{}' version '{}' in cache"
                .format(pkg_name, pkg_version)
            )
            return

        with TemporaryDirectory(prefix="deb2bolt-") as tmpdir:
            try:
                LOGGER.info("Fetching '%s'" % pkg_meta.url)

                with urllib.request.urlopen(pkg_meta.url) as response:
                    progress_bar = None

                    if response.length:
                        progress_bar = ProgressBar(response.length)
                        progress_bar(0)
                    #end if

                    deb_name = os.path.basename(pkg_meta.url)

                    with open(os.path.join(tmpdir, deb_name), "wb+") as f:
                        bytes_read = 0

                        for chunk in iter(lambda: response.read(8192), b""):
                            f.write(chunk)

                            if progress_bar:
                                bytes_read += len(chunk)
                                progress_bar(bytes_read)
                            #end if
                        #end for
                    #end with

                    deb_name = f.name
                #end with
            except urllib.error.URLError as e:
                raise NetworkError("error retrieving '%s': %s" % \
                        (pkg_meta.url, str(e)))

            self.contents = self._binary_deb_list_contents(deb_name)
        #end with
    #end function

    def as_xml(self, indent=0):
        self.contents.sort()

        install_deps = ""
        for dep in self.get("depends", []) + self.get("pre-depends", []):
            pkg_name, pkg_version = dep

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
            "binary_name":  self.get("name"),
            "section":      self.get("section"),
            "summary":      self.get("summary"),
            "description":  self.get("description", ""),
            "install_deps": install_deps,
            "contents":     contents
        }

        return BINARY_PKG_XML_TEMPLATE.format(**context)
    #end function

    # PRIVATE

    def _binary_deb_list_contents(self, filename):
        contents = []

        with TemporaryDirectory() as tmpdir:
            contents = self._binary_deb_list_contents_impl(filename, tmpdir)

        return contents
    #end function

    def _binary_deb_list_contents_impl(self, filename, tmpdir):
        data_name = None

        with ArchiveFileReader(filename) as archive:
            for entry in archive:
                if entry.pathname.startswith("data.tar"):                        
                    data_name = os.path.join(tmpdir, entry.pathname)

                    with open(data_name, "wb+") as f:
                        for chunk in iter(
                                lambda: archive.read_data(4096), b""):
                            f.write(chunk)
                        #end for
                    #end with

                    break
                #end if
            #end for
        #end with

        if not data_name:
            raise PackagingError("binary package %s contains no data." %
                    data_name)

        contents = []

        # parse data file entries and build content listing
        with ArchiveFileReader(data_name) as archive:
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
                    raise BoltValueError(
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
