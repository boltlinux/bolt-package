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
import time
from tempfile import TemporaryDirectory
from collections import OrderedDict
import org.boltlinux.package.libarchive as libarchive
from org.boltlinux.package.platform import Platform
from org.boltlinux.package.libarchive import ArchiveEntry, ArchiveFileWriter
from org.boltlinux.package.filestats import FileStats
from org.boltlinux.package.binarypackage import BinaryPackage
from org.boltlinux.package.metadata import PackageMetaData
from org.boltlinux.toolbox import switch

class DebianPackage(BinaryPackage):

    @property
    def debian_binary_version(self):
        return "2.0"

    def do_pack(self):
        self.pack_package()
        if self.make_debug_pkgs:
            self.pack_package(debug_pkg=True)
    #end function

    def pack_package(self, debug_pkg=False):
        epoch, version, release = self.version_tuple

        debug_suffix = "-dbg" if debug_pkg else ""
        pkg_filename = "_".join([self.name + debug_suffix,
            version + "-" + release, self.architecture]) + ".bolt"
        pkg_abspath  = self.output_dir + os.sep + pkg_filename
        meta_data    = self.meta_data(debug_pkg=debug_pkg)

        if not debug_pkg:
            contents = self.contents
        else:
            default_dir_attrs  = BinaryPackage.EntryAttributes({
                "deftype": "file",
                "mode":    "0755",
                "owner":   "root",
                "group":   "root",
                "conffile": False,
                "stats":    FileStats.default_dir_stats()
            })

            contents = {}

            for src, attr in self.contents.items():
                if not (attr.stats.is_file and attr.stats.is_elf_binary):
                    continue

                pkg_path = attr.dbg_info
                if not pkg_path:
                    continue

                dirname    = os.path.dirname(pkg_path)
                abs_path   = os.path.normpath(self.basedir + os.sep + pkg_path)
                file_stats = FileStats.detect_from_filename(abs_path) 
                file_attrs = BinaryPackage.EntryAttributes({
                    "deftype": "file",
                    "mode":    "0644",
                    "owner":   "root",
                    "group":   "root",
                    "conffile": False,
                    "stats":    file_stats
                })

                contents.setdefault(dirname, default_dir_attrs)
                contents.setdefault(pkg_path, file_attrs)
            #end for

            if not contents:
                return

            contents[self.install_prefix + "/lib/debug"] = \
                    default_dir_attrs
            contents[self.install_prefix + "/lib/debug/.build-id"] = \
                    default_dir_attrs
            contents = OrderedDict(sorted(set(contents.items()),
                key=lambda x: x[0]))
        #end if

        self.assemble_parts(meta_data, contents, pkg_abspath)
    #end function

    def assemble_parts(self, meta_data, pkg_contents, pkg_filename):
        with TemporaryDirectory(prefix="bolt-") as tmpdir:
            installed_size = self.write_data_part(pkg_contents,
                    os.path.join(tmpdir, "data.tar.gz"))

            # According to Debian Policy Manual Installed-Size is in KB
            installed_size = int(installed_size / 1024 + 0.5)

            meta_data["Installed-Size"] = "{}".format(installed_size)

            self.write_control_part(meta_data, pkg_contents,
                    os.path.join(tmpdir, "control.tar.gz"))

            with open(os.path.join(tmpdir, "debian-binary"), "w+",
                    encoding="utf-8") as fp:
                fp.write(self.debian_binary_version + "\n")
            #end with

            with ArchiveFileWriter(pkg_filename, libarchive.FORMAT_AR_SVR4,
                    libarchive.COMPRESSION_NONE) as archive:
                with ArchiveEntry() as archive_entry:
                    for entry_name in ["debian-binary", "control.tar.gz",
                            "data.tar.gz"]:
                        archive_entry.clear()

                        full_path = os.path.normpath(os.sep.join([tmpdir,
                            entry_name]))
                        archive_entry.copy_stat(full_path)
                        archive_entry.pathname = entry_name
                        archive_entry.mode = stat.S_IFREG | 0o644
                        archive_entry.uid = 0
                        archive_entry.gid = 0
                        archive_entry.uname = "root"
                        archive_entry.gname = "root"
                        archive.write_entry(archive_entry)

                        with open(full_path, "rb") as fp:
                            while True:
                                buf = fp.read(4096)
                                if not buf:
                                    break
                                archive.write_data(buf)
                            #end while
                        #end with
                    #end for
                #end with
            #end with
        #end with
    #end function

    def write_control_part(self, meta_data, pkg_contents, ctrl_abspath):
        with ArchiveFileWriter(ctrl_abspath, libarchive.FORMAT_TAR_USTAR,
                libarchive.COMPRESSION_GZIP) as archive:

            control_contents = [("control", meta_data.as_string(), 0o644)]

            for script_name, script_content in self.maintainer_scripts.items():
                control_contents.append([script_name, script_content, 0o754])

            conffiles = self.conffiles(pkg_contents)
            if conffiles:
                control_contents.append(["conffiles", conffiles, 0o644])

            timestamp = int(time.time())

            with ArchiveEntry() as archive_entry:
                for entry_name, entry_contents, entry_mode in control_contents:
                    entry_contents = entry_contents.encode("utf-8")
                    archive_entry.clear()
                    archive_entry.pathname = entry_name
                    archive_entry.mode = stat.S_IFREG | entry_mode
                    archive_entry.atime = timestamp
                    archive_entry.mtime = timestamp
                    archive_entry.ctime = timestamp
                    archive_entry.uid = 0
                    archive_entry.gid = 0
                    archive_entry.uname = "root"
                    archive_entry.gname = "root"
                    archive_entry.size = len(entry_contents)
                    archive.write_entry(archive_entry)
                    archive.write_data(entry_contents)
                #end for
            #end with
        #end with
    #end function

    def write_data_part(self, pkg_contents, data_abspath):
        installed_size = 0

        with ArchiveFileWriter(data_abspath, libarchive.FORMAT_TAR_USTAR,
                libarchive.COMPRESSION_GZIP) as archive:

            timestamp = int(time.time())

            with ArchiveEntry() as archive_entry:
                for src, attr in pkg_contents.items():
                    deftype    = attr.deftype
                    file_path  = "." + src
                    file_mode  = attr.mode
                    file_owner = attr.owner
                    file_group = attr.group
                    real_path  = os.path.normpath(self.basedir + os.sep + src)

                    archive_entry.clear()
                    if deftype != "file" and not os.path.exists(real_path):
                        archive_entry.mode = stat.S_IFDIR | 0o755
                        archive_entry.atime = timestamp
                        archive_entry.mtime = timestamp
                        archive_entry.ctime = timestamp
                    else:
                        archive_entry._copy_raw_stat(attr.stats)
                    #end if

                    archive_entry.pathname = file_path
                    archive_entry.uname = file_owner if file_owner else "root"
                    archive_entry.gname = file_group if file_group else "root"

                    if file_mode:
                        archive_entry.mode = archive_entry.filetype | file_mode
                    if archive_entry.is_symbolic_link:
                        archive_entry.symlink = attr.stats.link_target

                    archive.write_entry(archive_entry)

                    if archive_entry.is_file:
                        with open(real_path, "rb") as fp:
                            while True:
                                buf = fp.read(4096)
                                if not buf:
                                    break
                                archive.write_data(buf)
                            #end while
                        #end with
                    #end if

                    # imitate behavior of dpkg-gencontrol
                    if attr.stats.is_file or attr.stats.is_symbolic_link:
                        installed_size += attr.stats.st_size
                    else:
                        installed_size += 1024
                #end for
            #end with
        #end with

        return installed_size
    #end function

    def meta_data(self, debug_pkg=False):
        dep_type_2_str = {
            "requires":  "Depends",
            "provides":  "Provides",
            "conflicts": "Conflicts",
            "replaces":  "Replaces"
        }

        meta = PackageMetaData()

        meta["Package"]      = self.name + "-dbg" if debug_pkg else self.name
        meta["Version"]      = self.version
        meta["Source"]       = self.source
        meta["Architecture"] = self.architecture
        meta["Maintainer"]   = self.maintainer

        if debug_pkg:
            meta["Section"]     = "debug"
            meta["Depends"]     = "%s (= %s)" % (self.name, self.version)
            meta["Description"] = "debug symbols for ELF binaries in "\
                    "package '%s'" % self.name
        else:
            meta["Section"] = self.section

            for dep_type in ["requires", "provides", "conflicts", "replaces"]:
                relations = self.relations.get(dep_type)

                if not (relations and relations.list):
                    continue

                meta[dep_type_2_str[dep_type]] = str(relations)
            #end for

            meta["Description"] = self.description.summary()

            full_description = self.description.full_description()
            if full_description:
                meta["Description"] += "\n" + full_description
        #end if

        return meta
    #end function

    def conffiles(self, pkg_contents):
        result = ""
        for src, attr in pkg_contents.items():
            if attr.stats.is_directory or attr.conffile == False:
                continue
            real_path = os.path.normpath(self.basedir + os.sep + src)
            if not os.path.isfile(real_path) or os.path.islink(real_path):
                continue
            if attr.conffile == None and src.startswith("/etc/"):
                attr.conffile = True
            if attr.conffile:
                result += src + "\n"
        #end for
        return result
    #end function

#end class
