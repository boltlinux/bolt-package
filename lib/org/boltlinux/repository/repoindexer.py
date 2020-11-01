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
import shlex
import subprocess
import hashlib
import functools
import locale

import org.boltlinux.toolbox.libarchive as libarchive

from tempfile import TemporaryDirectory, NamedTemporaryFile
from org.boltlinux.toolbox.libarchive import ArchiveFileReader, \
        ArchiveFileWriter, ArchiveEntry
from org.boltlinux.error import NotFound, BoltSyntaxError, BoltError
from org.boltlinux.package.xpkg import BaseXpkg
from org.boltlinux.package.debianpackagemetadata import DebianPackageMetaData

class RepoIndexer:

    def __init__(self, repo_dir, force_full=False, sign_with=None):
        if not os.path.isdir(repo_dir):
            raise NotFound("path '%s' does not exists or is not a directory."
                    % repo_dir)

        self._force_full = force_full
        self._repo_dir   = repo_dir
        self._sign_with  = sign_with
    #end function

    def update_package_index(self):
        if self._force_full:
            index, digest = {}, ""
        else:
            index, digest = self.load_package_index()

        for meta_data in self.scan(index=index):
            name    = meta_data["Package"]
            version = meta_data["Version"]

            index\
                .setdefault(name, {})\
                .setdefault(version, meta_data)
        #end for

        if not self._force_full:
            self.prune_package_index(index)

        self.store_package_index(index, current_digest=digest)
    #end function

    def load_package_index(self):
        packages_file = os.path.join(self._repo_dir, "Packages.gz")

        if not os.path.exists(packages_file):
            return {}

        buf = ""

        with ArchiveFileReader(packages_file, raw=True) as archive:
            for entry in archive:
                buf = archive.read_data()

        h = hashlib.sha256()
        h.update(buf)

        text = buf.decode("utf-8")
        index = {}

        for entry in re.split(r"\n\n+", text, flags=re.MULTILINE):
            meta_data = DebianPackageMetaData(entry)

            try:
                name    = meta_data["Package"]
                version = meta_data["Version"]
            except KeyError:
                continue

            index.setdefault(name, {})[version] = meta_data
        #end for

        return index, h.hexdigest()
    #end function

    def prune_package_index(self, index):
        for name in list(index.keys()):
            for version, meta_data in list(index[name].items()):
                abspath  = os.path.join(self._repo_dir, meta_data["Filename"])

                if not os.path.exists(abspath):
                    del index[name][version]
            #end for
        #end for
    #end function

    def store_package_index(self, index, current_digest=None):
        meta_data_list = []

        for name in sorted(index.keys()):
            for version in sorted(index[name].keys(), key=functools.cmp_to_key(
                    BaseXpkg.compare_versions)):
                meta_data_list.append(index[name][version])
            #end for
        #end for

        if not meta_data_list:
            return

        output = "\n".join([str(entry) for entry in meta_data_list])
        output = output.encode("utf-8")

        if current_digest is not None:
            h = hashlib.sha256()
            h.update(output)
            if h.hexdigest() == current_digest:
                return

        packages_gz  = os.path.join(self._repo_dir, "Packages.gz")
        tempfile_gz  = None
        packages_sig = os.path.join(self._repo_dir, "Packages.sig")
        tempfile_sig = None

        try:
            with NamedTemporaryFile(dir=self._repo_dir, delete=False) \
                    as tempfile_gz:
                pass

            options = [("gzip", "timestamp", None)]

            with ArchiveFileWriter(tempfile_gz.name, libarchive.FORMAT_RAW,
                    libarchive.COMPRESSION_GZIP, options=options) as archive:

                with ArchiveEntry() as archive_entry:
                    archive_entry.filetype = stat.S_IFREG
                    archive.write_entry(archive_entry)
                    archive.write_data(output)
                #end with
            #end with

            os.chmod(
                tempfile_gz.name,
                stat.S_IRUSR |
                stat.S_IWUSR |
                stat.S_IRGRP |
                stat.S_IROTH
            )

            if self._sign_with:
                signature = self._create_usign_signature(output)
                with NamedTemporaryFile(dir=self._repo_dir, delete=False) \
                        as tempfile_sig:
                    tempfile_sig.write(signature)

                os.chmod(
                    tempfile_sig.name,
                    stat.S_IRUSR |
                    stat.S_IWUSR |
                    stat.S_IRGRP |
                    stat.S_IROTH
                )
            #end if

            os.rename(tempfile_gz.name, packages_gz)
            if self._sign_with:
                os.rename(tempfile_sig.name, packages_sig)
        finally:
            if tempfile_gz and os.path.exists(tempfile_gz.name):
                os.unlink(tempfile_gz.name)
            if tempfile_sig and os.path.exists(tempfile_sig.name):
                os.unlink(tempfile_sig.name)
        #end try
    #end function

    def scan(self, index=None):
        if index is None:
            index = {}

        for path, dirs, files in os.walk(self._repo_dir, followlinks=True):
            for filename in files:
                if not filename.endswith(".bolt"):
                    continue

                try:
                    name, version, arch = filename[:-5].rsplit("_")
                except ValueError:
                    continue

                entry = index.get(name, {}).get(version, None)

                if entry is not None:
                    continue

                abs_path = os.path.join(path, filename)

                try:
                    control_data = self.extract_control_data(abs_path)
                except BoltSyntaxError:
                    continue

                yield control_data
            #end for
        #end for
    #end function

    def extract_control_data(self, filename):
        meta_data = None

        with TemporaryDirectory() as tmpdir:
            with ArchiveFileReader(filename) as archive:
                for entry in archive:
                    if not entry.pathname.startswith("control.tar."):
                        continue

                    data_file = os.path.join(tmpdir, entry.pathname)

                    with open(data_file, "wb+") as outfile:
                        while True:
                            buf = archive.read_data(4096)
                            if not buf:
                                break
                            outfile.write(buf)
                        #end while
                    #end with

                    pool_path = re.sub(
                        r"^" + re.escape(self._repo_dir) + r"/*",
                        "",
                        filename
                    )

                    meta_data = DebianPackageMetaData(
                        self._extract_control_data(data_file))

                    meta_data["Filename"] = pool_path

                    break
                #end for
            #end with
        #end with

        meta_data["SHA256"] = self._file_sha256_sum(filename)
        meta_data["Size"]   = os.path.getsize(filename)

        return meta_data
    #end function

    # PRIVATE

    def _extract_control_data(self, filename):
        with ArchiveFileReader(filename) as archive:
            for entry in archive:
                if not entry.pathname == "control":
                    continue

                meta_data = archive\
                    .read_data()\
                    .decode("utf-8")

                meta_data = \
                    re.sub(r"^\s+.*?$\n?", "", meta_data, flags=re.MULTILINE)

                return meta_data.strip()
            #end for
        #end with
    #end function

    def _file_sha256_sum(self, filename):
        h = hashlib.sha256()
        with open(filename, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()
    #end function

    def _create_usign_signature(self, data):
        signature = None

        with NamedTemporaryFile(dir=self._repo_dir) as tempfile:
            tempfile.write(data)
            tempfile.flush()

            sign_cmd = shlex.split(
                "usign -S -m '{}' -s '{}' -x -".format(
                    tempfile.name, self._sign_with
                )
            )
            try:
                proc = subprocess.run(
                    sign_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )
                signature = proc.stdout
            except subprocess.CalledProcessError as e:
                raise BoltError(
                    "failed to sign Packages file: {}"
                    .format(e.stderr.decode(locale.getpreferredencoding())
                        .strip())
                )
            #end try
        #end with

        return signature
    #end function

#end class
