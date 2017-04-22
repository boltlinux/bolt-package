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
import shutil
from lxml import etree
from com.nonterra.bolt.package.error import XPackError
from com.nonterra.bolt.package.sourcepackage import SourcePackage
from com.nonterra.bolt.package.debianpackage import DebianPackage
from com.nonterra.bolt.package.shlibcache import ShlibCache
from com.nonterra.bolt.package.specfile import Specfile
from com.nonterra.bolt.package.changelog import Changelog
from com.nonterra.bolt.package.sourcecache import SourceCache
from com.nonterra.bolt.package.platform import Platform
from com.nonterra.bolt.package.appconfig import AppConfig
from com.nonterra.bolt.package.error import MissingDependencies

class PackageControl:

    def __init__(self, filename, parms={}):
        self.parms = {
            "outdir": None,
            "ignore_deps": False,
            "format": "deb",
            "debug_pkgs": True,
            "build_for": "target",
            "packages": []
        }
        self.parms.update(parms)

        xml_doc   = Specfile(filename).xml_doc
        self.info = {}

        # copy maintainer, email, version, revision to package sections
        for attr_name in ["maintainer", "email", "epoch",
                "version", "revision"]:
            xpath = "/control/changelog/release[1]/@%s" % attr_name
            try:
                attr_val = xml_doc.xpath(xpath)[0]
            except IndexError:
                continue
            xpath = "/control/*[name() = 'source' or name() = 'package']"
            for pkg_node in xml_doc.xpath(xpath):
                pkg_node.attrib[attr_name] = attr_val
        #end for

        # copy name and architecture-independent to binary packages sections
        xpath = "/control/source/@name"
        source_name = xml_doc.xpath(xpath)[0]
        xpath = "/control/source/@architecture-independent"
        try:
            is_arch_indep = xml_doc.xpath(xpath)[0].lower()
        except IndexError:
            is_arch_indep = "false"
        #end try
        for pkg_node in xml_doc.xpath("/control/package"):
            pkg_node.attrib["source"] = source_name

            if self.parms["build_for"] in ["tools", "cross-tools"]:
                pkg_node.attrib["architecture"] = "tools"
            elif is_arch_indep.lower() == "true":
                pkg_node.attrib["architecture"] = "all"
            else:
                pkg_node.attrib["architecture"] = Platform.target_machine()
        #end for

        xml_doc.xpath("/control/changelog")[0].attrib["source"] = source_name

        self.defines = {
            "BOLT_SOURCE_DIR":  "sources",
            "BOLT_BUILD_DIR":   "sources",
            "BOLT_INSTALL_DIR": "install",
            "BOLT_WORK_DIR":    os.getcwd(),
            "BOLT_BUILD_TYPE":  Platform.target_type(),
            "BOLT_BUILD_FOR":   self.parms["build_for"]
        }

        if self.parms["build_for"] == "tools":
            self.defines["BOLT_HOST_TYPE"] = Platform.tools_type()
            self.defines["BOLT_TARGET_TYPE"] = Platform.tools_type()
            self.defines["BOLT_INSTALL_PREFIX"] = "/tools"
        elif self.parms["build_for"] == "cross-tools":
            self.defines["BOLT_HOST_TYPE"] = Platform.tools_type()
            self.defines["BOLT_TARGET_TYPE"] = Platform.target_type()
            self.defines["BOLT_INSTALL_PREFIX"] = "/tools"
        else:
            self.defines["BOLT_HOST_TYPE"] = Platform.target_type()
            self.defines["BOLT_TARGET_TYPE"] = Platform.target_type()
            self.defines["BOLT_INSTALL_PREFIX"] = "/usr"
        #end if

        for node in xml_doc.xpath("/control/defines/def"):
            self.defines[node.get("name")] = node.get("value", "")

        # these *must* be absolute paths
        for s in ["SOURCE", "BUILD", "INSTALL"]:
            if os.path.isabs(self.defines["BOLT_%s_DIR" % s]):
                self.defines["BOLT_%s_DIR" % s] = os.path.realpath(
                        self.defines["BOLT_%s_DIR" % s])
            else:
                self.defines["BOLT_%s_DIR" % s] = os.path.realpath(
                    os.sep.join([self.defines["BOLT_WORK_DIR"],
                        self.defines["BOLT_%s_DIR" % s]])
                )
            #end if
        #end for

        self.src_pkg = SourcePackage(xml_doc.xpath("/control/source")[0])
        self.src_pkg.basedir = self.defines["BOLT_WORK_DIR"]

        self.bin_pkgs = []
        for node in xml_doc.xpath("/control/package"):
            pkg = DebianPackage(
                node,
                debug_pkgs=self.parms["debug_pkgs"],
                install_prefix=self.defines["BOLT_INSTALL_PREFIX"],
                host_type=self.defines["BOLT_HOST_TYPE"]
            )

            if self.parms["packages"]:
                if not pkg.name in self.parms["packages"]:
                    continue

            if pkg.build_for and not self.parms["build_for"] in pkg.build_for:
                continue

            if self.parms["build_for"] == "tools":
                pkg.name = "tools-" + pkg.name
            elif self.parms["build_for"] == "cross-tools":
                pkg.name = "tools-target-" + pkg.name
            #end if

            pkg.basedir = self.defines["BOLT_INSTALL_DIR"]

            if self.parms.get("outdir"):
                pkg.output_dir = os.path.realpath(self.parms["outdir"])
            else:
                pkg_output_dir = None
            #end if

            self.bin_pkgs.append(pkg)
        #end for

        if self.parms["packages"]:
            bin_pkg_names = [p.name for p in self.bin_pkgs]
            for p in self.parms["packages"]:
                if not p in bin_pkg_names:
                    raise XPackError("unknown binary package '%s'." % p)
            #end for
        #end if

        self.changelog = Changelog(xml_doc.xpath('/control/changelog')[0])
    #end function

    def __call__(self, action):
        if action not in ["list_deps", "clean"]:
            if not self.parms.get("ignore_deps"):
                dep_spec = self.src_pkg.missing_build_dependencies()
                if dep_spec.list:
                    msg = "missing dependencies: %s" % str(dep_spec)
                    raise MissingDependencies(msg)
                #end if
            #end if
        #end if

        getattr(self, action)()
    #end function

    def list_deps(self):
        print(self.src_pkg.build_dependencies())

    def unpack(self):
        directory = self.defines["BOLT_WORK_DIR"]
        if not os.path.exists(directory):
            os.makedirs(directory)

        cache_dir = os.path.realpath(AppConfig.get_config_folder() + \
                os.sep + "cache")
        repo_conf = self.parms.get("repositories", [])
        source_cache = SourceCache(cache_dir, repo_conf)

        self.src_pkg.unpack(directory, source_cache)
        self.src_pkg.patch(directory)
    #end function

    def prepare(self):
        directory = self.defines["BOLT_BUILD_DIR"]
        if not os.path.exists(directory):
            os.makedirs(directory)
        self.src_pkg.run_action("prepare", self.defines)
    #end function

    def build(self):
        directory = self.defines["BOLT_BUILD_DIR"]
        if not os.path.exists(directory):
            os.makedirs(directory)
        self.src_pkg.run_action("build", self.defines)
    #end function

    def install(self):
        source_dir  = self.defines["BOLT_SOURCE_DIR"]
        build_dir   = self.defines["BOLT_BUILD_DIR"]
        install_dir = self.defines["BOLT_INSTALL_DIR"]

        if os.path.exists(install_dir):
            shutil.rmtree(install_dir)
        os.makedirs(install_dir)

        self.src_pkg.run_action("install", self.defines)
    #end function

    def package(self):
        shlib_cache = ShlibCache(prefix=self.defines["BOLT_INSTALL_PREFIX"])
        for pkg in self.bin_pkgs:
            pkg.prepare()
            shlib_cache.overlay_package(pkg)
        for pkg in self.bin_pkgs:
            pkg.pack(shlib_cache)
    #end function

    def repackage(self):
        self.install()
        self.package()
    #end function

    def clean(self):
        self.src_pkg.run_action("clean", self.defines)

    def default(self):
        self.unpack()
        self.prepare()
        self.build()
        self.install()
        self.package()
    #end function

#end class
