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
import re
import glob
import stat
import subprocess
from pathlib import Path
from collections import OrderedDict
from lxml import etree
from com.nonterra.bolt.package.error import XPackError
from com.nonterra.bolt.package.braceexpand import braceexpand
from com.nonterra.bolt.package.platform import Platform
from com.nonterra.bolt.package.packagemanager import PackageManager
from com.nonterra.bolt.package.basepackage import BasePackage
from com.nonterra.bolt.package.packagedesc import PackageDescription
from com.nonterra.bolt.package.filestats import FileStats
from com.nonterra.bolt.package.util import switch

class BinaryPackage(BasePackage):

    class EntryAttributes:

        def __init__(self, spec={}):
            self.deftype  = spec.get("deftype", "file")
            self.mode     = spec.get("mode")
            self.owner    = spec.get("owner")
            self.group    = spec.get("group")
            self.conffile = spec.get("conffile")
            self.stats    = spec.get("stats")
            self.dbg_info = None

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

        self.name         = bin_node.get("name")
        self.description  = PackageDescription(bin_node.find("description"))
        self.maintainer   = bin_node.get("maintainer") + " <" + \
                bin_node.get("email") + ">"
        self.version      = (epoch + ":" if int(epoch) > 0 else "") + version + \
                ("-" + revision if revision != None else "")
        self.section      = bin_node.get("section", "unknown")
        self.source       = bin_node.get("source")
        self.architecture = bin_node.get("architecture")

        if self.architecture == "tools":
            self.name = "tools-" + self.name

        self.make_debug_pkgs = params["debug_pkgs"]
        self.install_prefix  = params["install_prefix"]
        self.host_type       = params["host_type"]


        self.relations = {}
        for dep_type in ["requires", "provides", "conflicts", "replaces"]:
            dep_node = bin_node.find(dep_type)

            if dep_node is None:
                continue

            for pkg_node in dep_node.findall(".//package"):
                dep_version = pkg_node.get("version", "").strip()
                dep_name    = pkg_node.get("name").strip()

                if dep_version.endswith("=="):
                    is_own_package = False

                    for tmp_node in bin_node.getparent().iterfind("package"):
                        if tmp_node.get("name") == dep_name:
                            is_own_package = True
                            break
                    #end for

                    if is_own_package:
                        pkg_node.attrib["version"] = dep_version[:-1] \
                            + " " + self.version
                    else:
                        pkg_manager = PackageManager.instance()
                        tmp_version = pkg_manager\
                                .installed_version_of_package(dep_name)
                        if not tmp_version:
                            raise XPackError("cannot resolve dependency '%s'." \
                                    % dep_name)
                        pkg_node.attrib["version"] = dep_version[:-1] \
                            + " " + tmp_version
                    #end if
                #end if

                if self.architecture == "tools":
                    pkg_node.attrib["name"] = "tools-" + pkg_node.attrib["name"]
            #end for

            self.relations[dep_type] = BasePackage.DependencySpecification\
                    .from_xml(dep_node)
        #end for

        self.contents = {}
        self.content_spec = {}
        prefix_regex = re.compile("^" + re.escape("${prefix}"))

        for node in bin_node.findall('contents/*'):
            src = prefix_regex.sub(self.install_prefix, node.get("src").strip())

            if len(src) > 1:
                src = src.rstrip(os.sep)

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

        content_node = bin_node.find("contents")
        if content_node is not None:
            self.content_subdir = content_node.get("subdir")
        else:
            self.content_subdir = ""
        #end function

        self.basedir        = os.path.realpath(".")
        self.output_dir     = "."
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
        try:
            self.generate_file_list()
        except ValueError as e:
            raise XPackError("error generating file list: " + str(e))
        self.strip_debug_symbols_and_delete_rpath()
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
                        if not src in contents:
                            attr.stats = FileStats.detect_from_filename(abs_path)
                            contents.setdefault(src, attr)
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

        # make sure all directories are included, as well
        extra_contents = {}
        for k in contents:
            while k != "/" and k != "":
                k = os.path.dirname(k)

                if (not k in contents) and (not k in extra_contents):
                    abs_path = self.basedir + os.sep + k
                    if os.path.exists(abs_path):
                        extra_contents[k] = BinaryPackage.EntryAttributes({
                            "deftype":  "dir",
                            "mode":     None,
                            "owner":    None,
                            "group":    None,
                            "conffile": False,
                            "stats":    FileStats.detect_from_filename(abs_path)
                        })
                    #end if
                #end if
            #end while
        #end for
        contents.update(extra_contents)

        if self.architecture == "tools":
            # filter out /etc and /var directories, these are shared
            def filter_etc_var(item):
                return False if path.as_posix()[0:5] in ["/etc", "/var"] \
                        else True
            #end inline function
            self.contents = OrderedDict(sorted(filter(filter_etc_var,
                set(contents.items())), key=lambda x: x[0]))
        else:
            self.contents = \
                OrderedDict(sorted(set(contents.items()), key=lambda x: x[0]))
        #end if

        return self.contents
    #end function

    def strip_debug_symbols_and_delete_rpath(self):
        objcopy   = Platform.find_executable(self.host_type + "-objcopy")
        chrpath   = Platform.find_executable("chrpath")
        hardlinks = {}
        install_prefix = self.install_prefix.lstrip("/")

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
            pkg_path = os.sep + os.path.join(install_prefix, "lib", "debug",
                    ".build-id", build_id[0:2], build_id[2:] + ".debug")
            dbg_path = os.path.normpath(os.sep.join([self.basedir, pkg_path]))

            hardlinks[dev][ino] = 1
            attr.dbg_info = pkg_path

            os.makedirs(os.path.dirname(dbg_path), exist_ok=True)

            # if u+w bit is missing objcopy will bail out
            if not (attr.stats.mode & stat.S_IWUSR):
                os.chmod(src_path, attr.stats.mode | stat.S_IWUSR)

            # separate debug information
            cmd_list = [
                ([objcopy, "--only-keep-debug", src_path, dbg_path], True),
                ([objcopy, "--strip-unneeded",  src_path          ], True),
                ([chrpath, "-d", src_path                         ], False)
            ]

            for cmd, check_retval in cmd_list:
                subprocess.run(cmd, stderr=subprocess.STDOUT,
                        check=check_retval)

            # file size has changed
            attr.stats.restat(src_path)
        #end for
    #end function

    def shlib_deps(self, shlib_cache=None):
        objdump = Platform.find_executable(self.host_type + "-objdump")

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

                    found = False

                    for shared_obj in shlib_cache.get(lib_name, []):
                        if shared_obj.arch_word_size() != word_size:
                            continue
                        pkg_name, version = shared_obj.package_name_and_version()
                        if not pkg_name or not version or pkg_name == self.name:
                            continue
                        if not "requires" in self.relations:
                            self.relations["requires"] = \
                                    BasePackage.DependencySpecification()
                        self.relations["requires"][pkg_name] = \
                                BasePackage.Dependency(pkg_name, ">= %s" % version)
                        found = True
                    #end for

                    if not found:
                        raise XPackError("dependency '%s' not found in any "
                            "installed package." % lib_name)
                #end for
            #end with
        #end for
    #end function

#end class
