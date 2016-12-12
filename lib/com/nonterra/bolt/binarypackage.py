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
import glob
import subprocess
from pathlib import Path
from collections import OrderedDict
from lxml import etree
from com.nonterra.bolt.braceexpand import braceexpand
from com.nonterra.bolt.platform import Platform
from com.nonterra.bolt.basepackage import BasePackage
from com.nonterra.bolt.packagedesc import PackageDescription
from com.nonterra.bolt.filestats import FileStats
from com.nonterra.bolt.util import switch

class BinaryPackage(BasePackage):

    class EntryAttributes:

        def __init__(self, spec={}):
            self.deftype  = spec.get("deftype", "file")
            self.mode     = spec.get("mode")
            self.owner    = spec.get("owner")
            self.group    = spec.get("group")
            self.conffile = spec.get("conffile")
            self.stats    = spec.get("stats")

            if isinstance(self.conffile, str):
                self.conffile = True if self.conffile.lower() == "true" \
                        else False
            if isinstance(self.mode, str):
                self.mode = int("0o%s" % self.mode, 8)
        #end function

    #end class

    def __init__(self, xml_config, **kwargs):
        params = {"debug_pkgs": True}
        params.update(kwargs)

        if isinstance(xml_config, etree._Element):
            bin_node = xml_config
        elif isinstance(xml_config, str):
            bin_node = etree.fromstring(xml_config)
        else:
            msg = "expected 'etree._Element' or 'str' but got '%s'" % \
                    xml_config.__class__.__name__
            raise ValueError(msg)
        #end if

        epoch     = bin_node.get("epoch",    0)
        version   = bin_node.get("version", "")
        revision  = bin_node.get("revision", None)
        archindep = bin_node.get("architecture-independent", "false")

        self.name        = bin_node.get("name")
        self.description = PackageDescription(bin_node.find("description"))
        self.maintainer  = bin_node.get("maintainer") + " <" + \
                bin_node.get("email") + ">"
        self.version     = (epoch + ":" if epoch > 0 else "") + version + \
                ("-" + revision if revision != None else "")
        self.section     = bin_node.get("section", "unknown")
        self.source      = bin_node.get("source")
        self.is_arch_indep = True if archindep == "true" else False

        self.make_debug_pkgs = params["debug_pkgs"]

        self.relations = {}
        for dep_type in ["requires", "provides", "conflicts", "replaces"]:
            dep_node = bin_node.find(dep_type)

            if dep_node is None:
                continue

            for pkg_node in dep_node.findall(".//package"):
                if pkg_node.get("version") == "==":
                    pkg_node.attrib["version"] = "= " + self.version
            #end for

            self.relations[dep_type] = BasePackage.DependencySpecification\
                    .from_xml(dep_node)
        #end for

        self.contents = {}
        self.content_spec = {}
        for node in bin_node.findall('contents/*'):
            src = node.get("src").strip().rstrip(os.sep)

            # '<file>' nodes have precedence over '<dir>'
            entry = self.content_spec.get(src)
            if entry and entry.deftype == "file" and node.tag == "dir":
                continue

            self.content_spec[src] = BinaryPackage.EntryAttributes({
                "deftype":  node.tag,
                "mode":     node.get("mode"),
                "owner":    node.get("owner"),
                "group":    node.get("group"),
                "conffile": node.get("conffile")
            })
        #end for

        self.maintainer_scripts = {}
        for node in bin_node.findall("maintainer-scripts/*"):
            if node.tag in ["preinst", "postinst", "prerm", "postrm"]:
                self.maintainer_scripts[node.tag] = "#!/bin/sh -e\n" + \
                        etree.tostring(node, method="text", encoding="unicode")
            #end if
        #end for

        self.content_subdir = bin_node.find("contents", {}).get("subdir")
        self.basedir        = os.path.realpath(".")
        self.output_dir     = ".."
        self.host_arch      = Platform.config_guess()
    #end function

    @property
    def version_tuple(self):
        regexp = r"^(?:(\d+):)?([-.+~a-zA-Z0-9]+?)(?:-([.~+a-zA-Z0-9]+)){0,1}$"
        m = re.match(regexp, self.version)
        return m.group(1, 2, 3)
    #end function

    @property
    def basedir(self):
        return self._basedir
    #end function

    @basedir.setter
    def basedir(self, basedir):
        real_base_dir = os.path.realpath(basedir)
        if basedir:
            self._basedir = real_base_dir
        if self.content_subdir:
            self._basedir = real_base_dir + os.sep + self.content_subdir
    #end function

    @property
    def output_dir(self):
        return self._output_dir
    #end function

    @output_dir.setter
    def output_dir(self, output_dir):
        self._output_dir = os.path.realpath(output_dir)
    #end function

    def prepare(self):
        self.generate_file_list()
        self.strip_debug_symbols()
    #end function

    def pack(self, shlib_cache):
        self.shlib_deps(shlib_cache)
        self.do_pack()
    #end function

    def generate_file_list(self):
        contents = {}

        for src, attr in self.content_spec.items():
            rel_path = os.path.normpath(src.lstrip(os.sep))
            abs_path = os.path.normpath(os.sep.join([self.basedir, src]))

            deftype  = attr.deftype
            mode     = attr.mode
            owner    = attr.owner
            group    = attr.group
            conffile = attr.conffile

            listing  = []

            for case in switch(deftype):
                if case("dir"):
                    attr.stats = FileStats.default_dir_stats()
                    contents[src] = attr
                    break
                if case("file"):
                    if glob.escape(src) != src or "{" in src:
                        # entry is a glob pattern
                        if "{" in src:
                            expansions = list(braceexpand(rel_path))
                        else:
                            expansions = [rel_path]
                        #end if
                        for pattern in expansions:
                            listing += list(Path(self.basedir).glob(pattern))
                    elif os.path.isdir(abs_path) and not \
                            os.path.islink(abs_path):
                        # entry is a real directory
                        listing = list(Path(self.basedir)\
                            .rglob(rel_path + "/**/*"))
                        attr.stats = FileStats.detect_from_filename(abs_path)
                        contents[src] = attr
                    else:
                        # entry is a symlink or file
                        attr.stats = FileStats.detect_from_filename(abs_path)
                        contents[src] = attr
                    break
            #end switch

            for path in listing:
                abs_path = path.as_posix()
                pkg_path = os.sep + path.relative_to(self.basedir).as_posix()

                if not pkg_path in contents:
                    stats = FileStats.detect_from_filename(abs_path)
                    contents[pkg_path] = BinaryPackage.EntryAttributes({
                        "deftype":  "file",
                        "mode":     mode,
                        "owner":    owner,
                        "group":    group,
                        "conffile": False if not stats.is_file else conffile,
                        "stats":    stats
                    })
                #end if
            #end for
        #end for

        self.contents = \
            OrderedDict(sorted(set(contents.items()), key=lambda x: x[0]))

        return self.contents
    #end function

    def strip_debug_symbols(self):
        objcopy   = Platform.find_executable("objcopy")
        hardlinks = {}

        # strip unstripped objects
        for src, attr in self.contents.items():
            if not (attr.stats.is_file and attr.stats.is_elf_binary):
                continue
            if attr.stats.is_stripped:
                continue

            dev = attr.stats.device
            ino = attr.stats.inode

            # no need to strip hardlinked content again
            if hardlinks.setdefault(dev, {}).get(ino):
                continue

            build_id = attr.stats.build_id
            src_path = os.path.normpath(os.sep.join([self.basedir, src]))
            pkg_path = os.sep + os.path.join("usr", "lib", "debug",
                    ".build-id", build_id[0:2], build_id[2:] + ".debug")
            dbg_path = os.path.normpath(os.sep.join([self.basedir, pkg_path]))

            hardlinks[dev][ino] = 1
            attr.dbg_info = pkg_path

            os.makedirs(os.path.dirname(dbg_path), exist_ok=True)

            # separate debug information
            cmd_list = [
                [objcopy, "--only-keep-debug", src_path, dbg_path],
                [objcopy, "--strip-unneeded",  src_path          ]
            ]

            for cmd in cmd_list:
                subprocess.run(cmd, stderr=subprocess.STDOUT, check=True)

            # file size has changed
            attr.stats.restat(src_path)
        #end for
    #end function

    def shlib_deps(self, shlib_cache=None):
        objdump = Platform.find_executable("objdump")

        for src, attr in self.contents.items():
            if not attr.stats.is_file or not attr.stats.is_elf_binary:
                continue

            abs_path  = os.path.normpath(self.basedir + os.sep + src)
            word_size = attr.stats.arch_word_size
            cmd       = [objdump, "-p", abs_path]

            with subprocess.Popen(cmd, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, universal_newlines=True) as proc:
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        break

                    m = re.match(r"^\s*NEEDED\s+(\S+)", line)
                    if not m:
                        continue
                    lib_name = m.group(1)

                    for shared_obj in shlib_cache.get(lib_name, []):
                        if shared_obj.arch_word_size() != word_size:
                            continue
                        pkg_name, version = shared_obj.package_name_and_version()
                        if not pkg_name or not version or pkg_name == self.name:
                            continue
                        self.relations["requires"][pkg_name] = \
                                BasePackage.Dependency(pkg_name, ">= %s" % version)
                    #end for
                #end for
            #end with
        #end for
    #end function

#end class
