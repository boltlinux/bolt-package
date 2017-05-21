# -*- encoding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2016 Tobias Koch <tobias.koch@nonterra.com>
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
import subprocess
from lxml import etree
import com.nonterra.bolt.package.libarchive as libarchive
from com.nonterra.bolt.package.libarchive import ArchiveEntry, ArchiveFileReader
from com.nonterra.bolt.package.packagedesc import PackageDescription
from com.nonterra.bolt.package.basepackage import BasePackage
from com.nonterra.bolt.package.platform import Platform
from com.nonterra.bolt.package.progressbar import ProgressBar
from com.nonterra.bolt.package.error import SourcePackageError

class SourcePackage(BasePackage):

    BOLT_HELPERS_SEARCH_PATH = [
        os.path.normpath(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "..", "..", "..", "..", "..", "helpers"
            )
        ),
        os.path.join(os.sep, "usr", "share", "bolt-pack", "helpers"),
        os.path.join(os.sep, "tools", "share", "bolt-pack", "helpers")
    ]

    def __init__(self, xml_config, verbose=True):
        if isinstance(xml_config, etree._Element):
            source_node = xml_config
        elif isinstance(xml_config, str):
            source_node = etree.fromstring(xml_config)
        else:
            msg = "expected 'etree._Element' or 'str' but got '%s'" % \
            xml_config.__class__.__name__
            raise ValueError(msg)
        #end if

        self.verbose = verbose
        self.basedir = "."
        self.name = source_node.get("name")
        self.description = PackageDescription(
                source_node.xpath("description")[0])

        try:
            req_node = source_node.xpath("requires")[0]
        except IndexError:
            req_node = "<requires></requires>"

        self.relations = {}
        self.relations["requires"] = BasePackage.DependencySpecification\
                .from_xml(req_node)

        self.patches = []
        for patch_set in source_node.xpath("patches/patchset"):
            patch_set_subdir = patch_set.get("subdir", "")
            patch_set_strip  = patch_set.get("strip", "1")

            for file_node in patch_set.xpath("file"):
                self.patches.append([
                    file_node.get("src", ""),
                    file_node.get("subdir", patch_set_subdir),
                    file_node.get("strip", patch_set_strip)
                ])
            #end for
        #end for

        self.sources = []
        for file_node in source_node.xpath("sources/file"):
            self.sources.append([
                file_node.get("src", ""),
                file_node.get("subdir", ""),
                file_node.get("sha256sum", "")
            ])
        #end for

        self.version    = source_node.get("version", "")
        self.maintainer = source_node.get("maintainer", "") + " <" + \
                source_node.get("email", "") + ">"

        self.rules = {
            "prepare": "",
            "build":   "",
            "install": "",
            "clean":   ""  # actually not supported anymore
        }

        for node in source_node.xpath("rules/*"):
            if not node.tag in ["prepare", "build", "install", "clean"]:
                continue
            self.rules[node.tag] = \
                    etree.tostring(node, method="text", encoding="unicode")
        #end for
    #end function

    def missing_build_dependencies(self):
        return self.relations["requires"].unfulfilled_dependencies()

    def build_dependencies(self):
        return self.relations["requires"]

    def unpack(self, source_dir=".", source_cache=None):
        for src_name, subdir, sha256sum in self.sources:
            archive_file = source_cache.find_and_retrieve(self.name,
                    self.version, src_name, sha256sum)
            source_dir_and_subdir = \
                    os.path.normpath(source_dir + os.sep + subdir)
            os.makedirs(source_dir_and_subdir, exist_ok=True)

            if not (archive_file and os.path.isfile(archive_file)):
                msg = "source archive for '%s' not found." % src_name
                raise SourcePackageError(msg)
            #end if

            total_size = 0
            with ArchiveFileReader(archive_file) as archive:
                for entry in archive:
                    if entry.is_file:
                        total_size += entry.size
                #end for
            #end with

            if self.verbose:
                sys.stdout.write("Upacking '%s' (%s): %s\n" %
                        (self.name, self.version, src_name))

            with ArchiveFileReader(archive_file) as archive:
                progress_bar = ProgressBar(total_size)
                bytes_read   = 0

                if self.verbose:
                    progress_bar(bytes_read)

                for entry in archive:
                    pathname = re.sub(r"^(?:\.+)?(?:/+)?[^/]*", "",
                            entry.pathname.strip())
                    if not pathname:
                        continue

                    full_path = os.path.normpath(source_dir_and_subdir + 
                            os.sep + pathname)
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)

                    if entry.is_directory:
                        entry.mode |= 0o700
                        os.makedirs(full_path, exist_ok=True)
                    elif entry.is_file:
                        entry.mode |= 0o600
                        with open(full_path, "wb+") as fp:
                            while True:
                                buf = archive.read_data(4096)
                                if not buf:
                                    break
                                bytes_read += len(buf)
                                fp.write(buf)
                            #end while
                        #end with
                        if self.verbose:
                            progress_bar(bytes_read)
                    elif entry.is_symbolic_link:
                        if os.path.exists(full_path):
                            os.unlink(full_path)
                        os.symlink(entry.symlink, full_path)
                        # IMPORTANT: don't do chmod on the symlink
                        continue
                    else:
                        msg = "file '%s' has unsupported file type."
                        raise SourcePackageError(msg)
                    #end if

                    os.chmod(full_path, entry.mode)
                #end for
            #end with
        #end for
    #end function

    def patch(self, source_dir="."):
        patch = Platform.find_executable("patch")

        sys.stdout.flush()
        sys.stderr.flush()

        for patch_file, subdir, strip_components in self.patches:
            if not os.path.isabs(patch_file):
                patch_file = os.path.normpath(self.basedir + 
                        os.sep + patch_file)
            #end if

            e_source_dir = source_dir if not subdir else source_dir + \
                    os.sep + subdir
            cmd = [patch, "-f", "-p%s" % strip_components, "-d", e_source_dir,
                    "-i", patch_file]
            try:
                subprocess.run(cmd, stderr=subprocess.STDOUT, check=True)
            except subprocess.CalledProcessError:
                raise SourcePackageError("couldn't apply patch.")
        #end for
    #end function

    def run_action(self, action, env=None):
        if env is None:
            env = {}

        if not action in ["prepare", "build", "install", "clean"]:
            raise SourcePackageError("invalid package action '%s'." % 
                    str(action))
        #end if

        env    = self.__update_env(env)
        script = self.__load_helpers() + "\n" + self.rules[action]
        cmd    = ["/bin/sh", "-e", "-x", "-s"]

        sys.stdout.flush()
        sys.stderr.flush()

        try:
            subprocess.run(cmd, env=env, input=script.encode("utf-8"),
                    stderr=subprocess.STDOUT, check=True)
        except subprocess.CalledProcessError:
            msg = "failed to %s the source package." % action
            raise SourcePackageError(msg)
        #end try
    #end function

    # PRIVATE

    def __load_helpers(self):
        result = []

        for script in ["arch.sh", "python.sh"]:
            for path in SourcePackage.BOLT_HELPERS_SEARCH_PATH:
                abs_path = os.path.join(path, script)
                if not os.path.isfile(abs_path):
                    continue
                with open(abs_path, "r", encoding="utf-8") as fp:
                    result.append(fp.read())
                    break
            #end for
        #end for

        return "\n".join(result)
    #end function

    def __update_env(self, env):
        env.update(Platform.build_flags())

        num_parallel_jobs = str(int(Platform.num_cpus() * 1.5))
        env["BOLT_PARALLEL_JOBS"] = num_parallel_jobs

        for k, v in os.environ.items():
            if k in ["BOLT_WORK_DIR", "BOLT_SOURCE_DIR", "BOLT_BUILD_DIR",
                    "BOLT_INSTALL_DIR"]:
                continue
            if k.startswith("BOLT_") or k in ["PATH", "USER", "USERNAME"]:
                env[k] = v
        #end for

        if env.get("PATH") is None:
            env["PATH"] = "/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin"

        return env
    #end function

#end function
