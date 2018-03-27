# -*- encoding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2016 Tobias Koch <tobias.koch@gmail.com>
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
import sys
import re
import stat
import locale
import subprocess
import urllib.request
from tempfile import TemporaryDirectory

import org.boltlinux.package.libarchive as libarchive
from org.boltlinux.package.progressbar import ProgressBar
from org.boltlinux.package.libarchive import ArchiveEntry, ArchiveFileReader
from org.boltlinux.deb2bolt.error import AptCacheNotFoundError, \
        DebianPackageContentMissing, PackageRetrievalError, Deb2BoltError

class PackageUtilsMixin:

    IMPLICIT_PATHS = {
        "/": 1,
        "/srv": 1,
        "/etc": 1,
        "/etc/skel": 1,
        "/etc/profile.d": 1,
        "/etc/opt": 1,
        "/sbin": 1,
        "/var": 1,
        "/var/misc": 1,
        "/var/spool": 1,
        "/var/spool/mail": 1,
        "/var/mail": 1,
        "/var/cache": 1,
        "/var/run": 1,
        "/var/www": 1,
        "/var/local": 1,
        "/var/lib": 1,
        "/var/tmp": 1,
        "/var/opt": 1,
        "/var/log": 1,
        "/mnt": 1,
        "/run": 1,
        "/run/mount": 1,
        "/home": 1,
        "/sys": 1,
        "/bin": 1,
        "/dev": 1,
        "/proc": 1,
        "/media": 1,
        "/lib": 1,
        "/tmp": 1,
        "/opt": 1,
        "/boot": 1,
        "/root": 1,
        "/usr": 1,
        "/usr/src": 1,
        "/usr/include": 1,
        "/usr/sbin": 1,
        "/usr/bin": 1,
        "/usr/share": 1,
        "/usr/share/misc": 1,
        "/usr/share/base-files": 1,
        "/usr/share/zoneinfo": 1,
        "/usr/share/terminfo": 1,
        "/usr/share/doc": 1,
        "/usr/share/locale": 1,
        "/usr/share/man": 1,
        "/usr/share/man/man7": 1,
        "/usr/share/man/man2": 1,
        "/usr/share/man/man8": 1,
        "/usr/share/man/man4": 1,
        "/usr/share/man/man6": 1,
        "/usr/share/man/man5": 1,
        "/usr/share/man/man1": 1,
        "/usr/share/man/man3": 1,
        "/usr/share/info": 1,
        "/usr/local": 1,
        "/usr/local/src": 1,
        "/usr/local/include": 1,
        "/usr/local/sbin": 1,
        "/usr/local/bin": 1,
        "/usr/local/share": 1,
        "/usr/local/share/misc": 1,
        "/usr/local/share/zoneinfo": 1,
        "/usr/local/share/terminfo": 1,
        "/usr/local/share/doc": 1,
        "/usr/local/share/locale": 1,
        "/usr/local/share/man": 1,
        "/usr/local/share/man/man7": 1,
        "/usr/local/share/man/man2": 1,
        "/usr/local/share/man/man8": 1,
        "/usr/local/share/man/man4": 1,
        "/usr/local/share/man/man6": 1,
        "/usr/local/share/man/man5": 1,
        "/usr/local/share/man/man1": 1,
        "/usr/local/share/man/man3": 1,
        "/usr/local/share/info": 1,
        "/usr/local/lib": 1,
        "/usr/lib": 1,
        "/usr/doc": 1,
        "/usr/man": 1,
        "/usr/info": 1
    }

    def is_path_implicit(self, path):
        return True if path in PackageUtilsMixin.IMPLICIT_PATHS else False

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
        if path  == "/usr/share/locale" or \
                path.startswith("/usr/share/locale/"):
            return True
        else:
            return False
    #end function

    def is_menu_path(self, path):
        if path == "/usr/share/menu" or path.startswith("/usr/share/menu/"):
            return True
        else:
            return False
    #end function

    def is_mime_path(self, path):
        if path == "/usr/lib/mime" or path.startswith("/usr/lib/mime/"):
            return True
        else:
            return False
    #end function

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

    def is_pkg_name_debian_specific(self, name):
        if name.startswith("dpkg"):
            return True
        if name.startswith("debhelper"):
            return True
        if name.endswith("debconf"):
            return True
        if name.startswith("dh-"):
            return True
        if name in ["quilt", "lsb-release"]:
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

    def get_content_spec_local_guesswork(self, debdir, pkg_name, pkg_version,
            **kwargs):
        contents = []

        extensions = [
            ".files",
            ".install",
            ".dirs",
            ".files.in",
            ".install.in",
            ".dirs.in"
        ]

        install_file_list = [pkg_name + ext for ext in extensions] + \
                ["files", "install", "dirs"]

        for filename in install_file_list:
            abs_path = os.path.join(debdir, filename)
            if not os.path.exists(abs_path):
                continue

            parts = filename.split(".")
            content_type = parts[-2] if parts[-1] == "in" else parts[-1]

            with open(abs_path, "r", encoding="utf-8") as f:
                lines = []
                for entry_path in f.readlines():
                    entry_path = entry_path.strip()
                    if not entry_path:
                        continue

                    m = re.match(r"^(\S+)\s+(\S+)$", entry_path)
                    if m:
                        entry_path = m.group(1)

                    entry_path = self.fix_path(entry_path)

                    if self.is_path_implicit(entry_path):
                        continue

                    if content_type == "dirs":
                        entry_type  = stat.S_IFDIR
                        entry_mode  = 0o755
                        entry_uname = "root"
                        entry_gname = "root"
                    else:
                        #
                        # We don't know whether it's a dir or a file and I do
                        # not want to guess. Move on.
                        #
                        entry_type  = 0
                        entry_mode  = 0
                        entry_uname = "root"
                        entry_gname = "root"
                    #end if

                    contents.append([entry_path, entry_type, entry_mode,
                        entry_uname, entry_gname])
                #end for

                return contents
            #end with
        #end for

        return contents
    #end function

    def get_content_spec_via_package_pool(self, pkg_name, pkg_version, mirror):
        contents = []

        apt_cmd = ["apt-cache", "--no-all-versions", "show",  "%s" % pkg_name]
        try:
            apt_output = subprocess.run(apt_cmd, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, check=True)\
                            .stdout\
                            .decode(locale.getpreferredencoding())\
                            .strip()
        except subprocess.CalledProcessError as e:
            raise AptCacheNotFoundError("error looking up %s=%s: %s" % \
                    (pkg_name, pkg_version, str(e)))
        #end try

        pool_path = ""

        for line in apt_output.splitlines():
            line = line.strip()
            try:
                k, v = line.split(":", 1)
            except ValueError:
                continue
            k = k.strip()
            v = v.strip()
            if k.lower() == "filename":
                pool_path = v
        #end for

        if not pool_path:
            raise AptCacheNotFoundError(
                    "could not find pool location for %s=%s" % \
                            (pkg_name, pkg_version))

        pool_url = mirror + pool_path

        with TemporaryDirectory(prefix="deb2bolt-") as tmpdir:
            try:
                sys.stdout.write("Fetching '%s' ...\n" % pool_url)

                with urllib.request.urlopen(pool_url) as response:
                    bytes_read = 0

                    progress_bar = ProgressBar(response.length) if \
                            response.length else None
                    if progress_bar:
                        progress_bar(bytes_read)

                    deb_name = os.path.basename(pool_path)

                    with open(os.path.join(tmpdir, deb_name), "wb+") \
                            as outfile:
                        while True:
                            buf = response.read(4096)
                            if not buf:
                                break
                            outfile.write(buf)
                            bytes_read += len(buf)
                            if progress_bar:
                                progress_bar(bytes_read)
                        #end while
                    #end with

                    deb_name = outfile.name
                #end with
            except urllib.error.URLError as e:
                raise PackageRetrievalError("error retrieving '%s': %s" % \
                        (pool_url, str(e)))

            contents = self.__binary_deb_list_contents(deb_name, tmpdir)
        #end with

        return contents
    #end function

    def binary_deb_list_contents(self, filename):
        contents = []
        with TemporaryDirectory() as tmpdir:
            contents = self.__binary_deb_list_contents(filename, tmpdir)
        return contents
    #end function

    def __binary_deb_list_contents(self, filename, tmpdir):
        # extract data file from deb
        with ArchiveFileReader(filename) as archive:
            data_name = None

            for entry in archive:
                if entry.pathname.startswith("data.tar"):                        
                    data_name = os.path.join(tmpdir, entry.pathname)

                    with open(data_name, "wb+") as outfile:
                        while True:
                            buf = archive.read_data(4096)
                            if not buf:
                                break
                            outfile.write(buf)
                        #end while
                    #end with

                    break
                #end if
            #end for
        #end with

        if not data_name:
            raise DebianPackageContentMissing(
                    "binary package %s contains no data." % data_name)

        contents = []

        # parse data file entries and build content listing
        with ArchiveFileReader(data_name) as archive:
            for entry in archive:
                entry_path  = self.fix_path(entry.pathname)

                if entry.is_directory and self.is_path_implicit(entry_path):
                    continue
                if self.is_doc_path(entry_path):
                    continue
                if self.is_l10n_path(entry_path):
                    continue
                if self.is_menu_path(entry_path):
                    continue

                entry_mode  = entry.mode
                entry_uname = entry.uname
                entry_gname = entry.gname

                if entry.is_directory:
                    entry_type = stat.S_IFDIR
                elif entry.is_symbolic_link:
                    entry_type = stat.S_IFLNK
                elif entry.is_file or entry.is_hardlink:
                    entry_type = stat.S_IFREG
                else:
                    raise Deb2BoltError("type of '%s' unknown '%d'" %
                            (entry_path, entry_type))

                contents.append([entry_path, entry_type, entry_mode,
                    entry_uname, entry_gname])
            #end for
        #end with

        return contents
    #end function

#end class

