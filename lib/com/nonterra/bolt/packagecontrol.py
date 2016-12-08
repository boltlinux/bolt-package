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
import shutil
from lxml import etree
from com.nonterra.bolt.sourcepackage import SourcePackage
from com.nonterra.bolt.debianpackage import DebianPackage
from com.nonterra.bolt.shlibcache import ShlibCache
from com.nonterra.bolt.specfile import Specfile
from com.nonterra.bolt.changelog import Changelog
from com.nonterra.bolt.sourcecache import SourceCache
from com.nonterra.bolt.platform import Platform
from com.nonterra.bolt.appconfig import AppConfig
from com.nonterra.bolt.error import MissingDependencies

class PackageControl:

    def __init__(self, filename, parms={}):
        self.parms = {
            "outdir": None,
            "ignore_deps": False,
            "format": "deb",
            "debug_pkgs": True
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
            pkg_node.attrib["architecture-independent"] = is_arch_indep
        #end for

        xml_doc.xpath("/control/changelog")[0].attrib["source"] = source_name

        self.defines = {
            "BOLT_SOURCE_DIR":  "sources",
            "BOLT_INSTALL_DIR": "install"
        }

        self.defines["BOLT_BUILD_TYPE"]  = self.parms.get("build_type")  or\
                Platform.config_guess()
        self.defines["BOLT_HOST_TYPE"]   = self.parms.get("host_type")   or\
                self.defines["BOLT_BUILD_TYPE"]
        self.defines["BOLT_TARGET_TYPE"] = self.parms.get("target_type") or\
                self.defines["BOLT_HOST_TYPE"]
        self.defines["BOLT_WORK_DIR"]    = os.getcwd()

        for node in xml_doc.xpath("/control/defines/def"):
            self.defines[node.get("name")] = node.get("value", "")

        self.defines.setdefault("BOLT_BUILD_DIR",
                self.defines["BOLT_SOURCE_DIR"])

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
            pkg = DebianPackage(node, debug_pkgs=self.parms["debug_pkgs"])
            pkg.basedir    = self.defines["BOLT_INSTALL_DIR"]
            if self.parms.get("outdir"):
                pkg.output_dir = os.path.realpath(self.parms["outdir"])
            else:
                pkg_output_dir = None
            #end if
            pkg.host_arch = self.defines["BOLT_HOST_TYPE"]
            self.bin_pkgs.append(pkg)
        #end for

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
        shlib_cache = ShlibCache()
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
