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
from lxml import etree
from org.boltlinux.error import InvocationError, MalformedSpecfile
from org.boltlinux.package.serialize import SpecfileSerializer

class Specfile:

    RELAXNG_SCHEMA_SEARCH_PATH = [
        os.path.normpath(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "..", "..", "..", "..", "relaxng", "package.rng.xml"
            )
        ),
        os.path.join(os.sep, "usr", "share", "bolt-pack", "relaxng",
            "package.rng.xml"),
        os.path.join(os.sep, "tools", "share", "bolt-pack", "relaxng",
            "package.rng.xml"),
    ]

    def __init__(self, filename):
        if not os.path.exists(filename):
            raise InvocationError("no such file '%s'." % filename)

        parser = etree.XMLParser(encoding="utf-8", load_dtd=True,
                no_network=True, ns_clean=True, strip_cdata=True,
                resolve_entities=True)

        try:
            xml_doc = etree.parse(filename, parser)
            xml_doc.xinclude()
        except (etree.XMLSyntaxError, etree.XIncludeError) as e:
            raise MalformedSpecfile(str(e))

        self.xml_doc = xml_doc

        self.validate_structure()
        self.validate_format()
    #end function

    def validate_structure(self):
        relaxng = None

        for path in Specfile.RELAXNG_SCHEMA_SEARCH_PATH:
            if os.path.exists(path):
                relaxng = etree.RelaxNG(file=path)
                break
        #end for

        if relaxng is None:
            raise RuntimeError("RELAX NG ruleset not found.")

        if not relaxng.validate(self.xml_doc):
            errors = []
            for err in relaxng.error_log:
                errors.append("* %s on line %d, column %d: %s" % 
                        (os.path.basename(err.filename), err.line,
                            err.column, err.message))
            #end for
            msg = "RELAX NG validation failed:\n" + "\n".join(errors)
            raise MalformedSpecfile(msg)
        #end if

        return True
    #end function

    def validate_format(self):
        errors = []

        specification = [
            ["//patchset/@strip", r"^[1-9]\d*$"],
            ["//patchset/file/@strip", r"^[1-9]\d*$"],
            ["//*[name() = 'source' or name() = 'package']/@name", r"^[a-zA-Z0-9]*(?:(?:\+|-|\.)[a-zA-Z0-9]*)*$" ],
            ["//binary//package/@version", r"(?:^(?:<<|<=|=|>=|>>)\s*(?:(\d+):)?([-.+~a-zA-Z0-9]+?)(?:-([.~+a-zA-Z0-9]+)){0,1}$)|(?:^==$)"],
            ["//source//package/@version", r"(?:^(?:<<|<=|=|>=|>>)\s*(?:(\d+):)?([-.+~a-zA-Z0-9]+?)(?:-([.~+a-zA-Z0-9]+)){0,1}$)"],
            ["//changelog/release/@epoch", r"^\d+$"],
            ["//changelog/release/@version", r"^([-.+~a-zA-Z0-9]+?)(?:-([.~+a-zA-Z0-9]+)){0,1}$"],
            ["//changelog/release/@revision", r"^[.~+a-zA-Z0-9]+$"],
            ["//changelog/release/@email", r"^[-_%.a-zA-Z0-9]+@[-.a-z0-9]+\.[a-z]{2,4}$"],
            ["//changelog/release/@date", r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s*(?:((?:-|\+)\d{2}:?\d{2})|(?:(?:GMT|UTC)(?:(?:-|\+)\d{1,2}))|[a-zA-Z]+)$"]
        ]

        for xpath, regexp in specification:
            for attr in self.xml_doc.xpath(xpath):
                if not re.match(regexp, attr):
                    path = attr.getparent().tag + "/@" + attr.attrname
                    line = attr.getparent().sourceline
                    errors.append("* %s on line %s: '%s' does not match '%s'." \
                            % (path, line, attr, regexp))
                #end if
            #end for
        #end for

        if errors:
            msg = "format errors:\n" + "\n".join(errors)
            raise MalformedSpecfile(msg)
        #end if

        return True
    #end function

    def serialize(self):
        return SpecfileSerializer(self.xml_doc).serialize()

    @property
    def source_name(self):
        return self.xml_doc.xpath("/control/source/@name")[0]

    @property
    def latest_version(self):
        epoch   = ""
        version = ""
        rev     = ""

        try:
            epoch = self.xml_doc\
                .xpath("/control/changelog/release[1]/@epoch")[0]
        except IndexError: pass

        version = self.xml_doc\
            .xpath("/control/changelog/release[1]/@version")[0]

        try:
            rev = self.xml_doc\
                .xpath("/control/changelog/release[1]/@revision")[0]
        except IndexError: pass

        if epoch:
            version = epoch + ":" + version
        if rev:
            version = version + "-" + rev

        return version
    #end function

    @property
    def binary_packages(self):
        pkg_names = []

        for pkg_node in self.xml_doc.xpath("/control/package"):
            pkg_names.append(pkg_node.attrib["name"])

        return pkg_names
    #end function

    @property
    def upstream_version(self):
        try:
            return self.xml_doc.xpath(
                "/control/changelog/release[1]/@upstream-version")[0]
        except IndexError:
            return None
    #end function

#end class
