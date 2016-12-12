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

from lxml import etree
from com.nonterra.bolt.package.packagemanager import PackageManager

class BasePackage:

    class Dependency:

        def __init__(self, name, version=None):
            self.name    = name
            self.version = version
        #end function

        @property
        def is_fulfilled(self):
            package_manager = PackageManager.instance()
            return package_manager\
                    .installed_version_meets_condition(self.name, self.version)
        #end function

    #end class

    class DependencySpecification:

        def __init__(self):
            self.list  = []
            self.index = {}
        #end function

        @classmethod
        def from_xml(klass, xml_config=""):
            spec = BasePackage.DependencySpecification()

            if isinstance(xml_config, etree._Element):
                dep_node = xml_config
            elif isinstance(xml_config, str):
                dep_node = etree.fromstring(xml_config)
            elif not xml_config:
                return spec
            else:
                msg = "expected 'etree._Element' or 'str' but got '%s'" % \
                        xml_config.__class__.__name__
                raise ValueError(msg)
            #end if

            for node in dep_node.xpath("package|choice"):
                alternatives = []
                if node.tag == "choice":
                    for pkg in node.xpath("package"):
                        alternatives.append(
                            BasePackage.Dependency(
                                pkg.attrib["name"],
                                pkg.get("version")
                            )
                        )
                    #end for
                else:
                    alternatives.append(
                        BasePackage.Dependency(
                            node.attrib["name"],
                            node.get("version")
                        )
                    )
                #end if

                for dep in alternatives:
                    spec.index[dep.name] = dep
                spec.list.append(alternatives)
            #end for

            return spec
        #end function

        def __iter__(self):
            self.list.sort(key=lambda x: x[0].name)

            for alternatives in self.list:
                yield alternatives
        #end function

        def __getitem__(self, key):
            return self.index[key]

        def __setitem__(self, key, value):
            if not key in self.index:
                self.index[key] = value
                self.list.append([value])
        #end function

        def unfulfilled_dependencies(self):
            unfulfilled_spec = BasePackage.DependencySpecification()

            for alternatives in self.list:
                fulfilled = False

                for dependency in alternatives:
                    if dependency.is_fulfilled:
                        fulfilled = True
                        break
                    #end if
                #end for

                if not fulfilled:
                    for dependency in alternatives:
                        unfulfilled_spec.index[dependency.name] = dependency
                    unfulfilled_spec.list.append(alternatives)
                #end if
            #end for

            return unfulfilled_spec
        #end function

        def __str__(self):
            if not self.list:
                return ""

            dep_list = []
            for alternatives in self.list:
                alt_list = []
                for alt in alternatives:
                    if alt.version:
                        alt_list.append("%(name)s (%(version)s)" %
                            {"name": alt.name, "version": alt.version}
                        )
                    else:
                        alt_list.append("%s" % alt.name)
                #end for
                dep_list.append(" | ".join(alt_list))
            #end for

            return ", ".join(dep_list)
        #end function
    #end class

#end class
