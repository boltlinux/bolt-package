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
import locale
import subprocess
from com.nonterra.bolt.package.platform import Platform
from com.nonterra.bolt.package.filestats import FileStats
from com.nonterra.bolt.package.packagemanager import PackageManager
from com.nonterra.bolt.package.error import ShlibCacheError

class ShlibCache:

    class SharedObject:

        def __init__(self, lib_path):
            self.lib_path    = lib_path
            self.pkg_name    = None
            self.pkg_version = None
            self.word_size   = None
        #end function

        def package_name(self):
            if self.pkg_name is None:
                pkg_manager = PackageManager.instance()
                self.pkg_name = \
                        pkg_manager.which_package_provides(self.lib_path)
            return self.pkg_name
        #end function

        def package_version(self):
            if self.pkg_version is None:
                pkg_manager = PackageManager.instance()
                self.pkg_version = pkg_manager\
                        .installed_version_of_package(self.package_name())
            return self.pkg_version
        #end function

        def package_name_and_version(self):
            return self.package_name(), self.package_version()

        def arch_word_size(self):
            if self.word_size is None:
                self.word_size = FileStats\
                        .detect_from_filename(os.path.realpath(self.lib_path))\
                        .arch_word_size
            return self.word_size
        #end function

    #end class

    def __init__(self, prefix="/usr"):
        self.prefix = prefix
        self.map = {}
        self.have_ldconfig = False

        ldconfig = Platform.find_executable("ldconfig")
        if ldconfig:
            self.have_ldconfig = True

            try:
                procinfo = subprocess.run([ldconfig, "-p"], stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, check=True)
            except subprocess.CalledProcessError as e:
                raise ShlibCacheError("failed to initialize shlib cache: " + str(e))

            output_lines = procinfo\
                    .stdout\
                    .decode(locale.getpreferredencoding(False))\
                    .splitlines()

            for line in output_lines:
                m = re.match(r"^\s*(\S+) \((.*)\) => (\S+)", line)
                if not m:
                    continue
                if "hwcap" in m.group(2):
                    continue

                lib_name = m.group(1)
                lib_path = m.group(3)

                if "libx" in lib_path:
                    continue

                self.map.setdefault(lib_name, [])\
                        .append(ShlibCache.SharedObject(lib_path))
            #end for
        #end if
    #end function

    def __getitem__(self, key):
        if self.have_ldconfig:
            return self.map[key]
        else:
            return self.map.get(key, self.__find_object(key))
    #end function

    def get(self, key, default=None):
        try:
            if self.have_ldconfig:
                return self.map[key]
            else:
                return self.map.get(key, self.__find_object(key))
        except KeyError:
            return default
    #end function

    def overlay_package(self, binary_package):
        for src, attr in binary_package.contents.items():
            if attr.stats.is_symbolic_link:
                abs_path = os.path.normpath(
                        binary_package.basedir + os.sep + src)
                if not os.path.exists(abs_path):
                    continue
                stats = FileStats.detect_from_filename(
                        os.path.realpath(abs_path))
            else:
                stats = attr.stats
            #end if

            if not stats.is_dynamically_linked:
                continue

            new_shared_obj             = ShlibCache.SharedObject(src)
            new_shared_obj.pkg_name    = binary_package.name
            new_shared_obj.pkg_version = binary_package.version
            new_shared_obj.word_size   = stats.arch_word_size
            lib_name                   = os.path.basename(src)

            shared_obj_list = self.map.setdefault(lib_name, [])

            for i in range(len(shared_obj_list)):
                tmp_shared_obj = shared_obj_list[i]

                if new_shared_obj.arch_word_size() == \
                        tmp_shared_obj.arch_word_size():
                    shared_obj_list[i] = new_shared_obj
                    new_shared_obj = None
                    break
                #end if
            #end for

            # wasn't there before, so add it!
            if new_shared_obj is not None:
                shared_obj_list.append(new_shared_obj)
        #end for
    #end function

    # PRIVATE

    def __find_object(self, lib_name):
        lib_path = [self.prefix + os.sep + "lib"]

        for path in lib_path:
            object_path = lib_path + os.sep + path
            if os.path.isfile(path):
                self.map.setdefault(lib_name, []) \
                        .append(ShlibCache.SharedObject(lib_path))
        #end for

        return self.map[lib_name]
    #end function

#end class
