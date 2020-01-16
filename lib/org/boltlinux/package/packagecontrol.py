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
import shutil

from org.boltlinux.error import UnmetDependency, InvocationError
from org.boltlinux.package.basepackage import BasePackage
from org.boltlinux.package.sourcepackage import SourcePackage
from org.boltlinux.package.debianpackage import DebianPackage
from org.boltlinux.package.shlibcache import ShlibCache
from org.boltlinux.package.specfile import Specfile
from org.boltlinux.package.changelog import Changelog
from org.boltlinux.package.sourcecache import SourceCache
from org.boltlinux.package.platform import Platform
from org.boltlinux.package.appconfig import AppConfig

class PackageControl:

    def __init__(self, filename, release_config, cache_dir=None, **kwargs):
        self.parms = {
            "build_for": "target",
            "debug_pkgs": True,
            "disable_packages": [],
            "enable_packages": [],
            "format": "deb",
            "ignore_deps": False,
            "outdir": None,
        }
        self.parms.update(kwargs)

        xml_doc     = Specfile(filename).xml_doc
        self.info   = {}
        self.config = release_config

        if not cache_dir:
            cache_dir = os.path.realpath(os.path.join(
                os.getcwd(), "source-cache"))

        self._cache_dir = cache_dir

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
            "BOLT_SOURCE_DIR": "sources",
            "BOLT_BUILD_DIR": "sources",
            "BOLT_INSTALL_DIR": "install",
            "BOLT_WORK_DIR": os.getcwd(),
            "BOLT_TOOLS_TYPE": Platform.tools_type(),
            "BOLT_BUILD_FOR": self.parms["build_for"]
        }

        if self.parms["build_for"] == "tools":
            self.defines["BOLT_BUILD_TYPE"] = Platform.tools_type(),
            self.defines["BOLT_HOST_TYPE"] = Platform.tools_type()
            self.defines["BOLT_TARGET_TYPE"] = Platform.tools_type()
            self.defines["BOLT_INSTALL_PREFIX"] = "/tools"
        elif self.parms["build_for"] == "cross-tools":
            self.defines["BOLT_BUILD_TYPE"] = Platform.tools_type(),
            self.defines["BOLT_HOST_TYPE"] = Platform.tools_type()
            self.defines["BOLT_TARGET_TYPE"] = Platform.target_type()
            self.defines["BOLT_INSTALL_PREFIX"] = "/tools"
        else:
            self.defines["BOLT_BUILD_TYPE"] = Platform.target_type(),
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

        self.src_pkg = SourcePackage(
            xml_doc.xpath("/control/source")[0],
            build_for=self.parms["build_for"]
        )
        self.src_pkg.basedir = self.defines["BOLT_WORK_DIR"]

        if self.parms["enable_packages"]:
            for p in self.parms["enable_packages"]:
                if not xml_doc.xpath("/control/package[@name='%s']" % p):
                    raise InvocationError("unknown binary package '%s'." % p)
            #end for
        #end if

        if self.parms["disable_packages"]:
            for p in self.parms["disable_packages"]:
                if not xml_doc.xpath("/control/package[@name='%s']" % p):
                    raise InvocationError("unknown binary package '%s'." % p)
            #end for
        #end if

        self.bin_pkgs = []
        for node in xml_doc.xpath("/control/package"):
            pkg = DebianPackage(
                node,
                debug_pkgs=self.parms["debug_pkgs"],
                install_prefix=self.defines["BOLT_INSTALL_PREFIX"],
                host_type=self.defines["BOLT_HOST_TYPE"],
                build_for=self.parms["build_for"]
            )

            if self.parms["enable_packages"]:
                if pkg.name not in self.parms["enable_packages"]:
                    continue
            if self.parms["disable_packages"]:
                if pkg.name in self.parms["disable_packages"]:
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

            self.bin_pkgs.append(pkg)
        #end for

        self.changelog = Changelog(xml_doc.xpath('/control/changelog')[0])
    #end function

    def __call__(self, action):
        if action not in ["list_deps", "unpack", "clean"]:
            if not self.parms.get("ignore_deps"):
                missing_deps = self._missing_build_dependencies()
                if missing_deps.list:
                    msg = "missing dependencies: {}".format(missing_deps)
                    raise UnmetDependency(msg)
                #end if
            #end if
        #end if

        getattr(self, action)()
    #end function

    def list_deps(self):
        print(self.src_pkg.build_dependencies())

    def unpack(self):
        release = self.config.get("id", "stable")

        directory = self.defines["BOLT_WORK_DIR"]
        if not os.path.exists(directory):
            os.makedirs(directory)

        repo_conf    = self.config.get("repositories", [])
        source_cache = SourceCache(self._cache_dir, repo_conf, release=release)

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
            pkg.pack(shlib_cache, self.bin_pkgs)
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

    # PRIVATE

    def _missing_build_dependencies(self):
        unfulfilled_dependency_spec = BasePackage.DependencySpecification()

        for alternatives in self.src_pkg.relations["requires"].list:
            fulfilled = False

            for dep in alternatives:
                if dep.is_fulfilled:
                    fulfilled = True
                    break
            #end for

            if not fulfilled:
                for dep in alternatives:
                    unfulfilled_dependency_spec.index[dep.name] = dep
                unfulfilled_dependency_spec.list.append(alternatives)
            #end if
        #end for

        return unfulfilled_dependency_spec
    #end function

#end class
