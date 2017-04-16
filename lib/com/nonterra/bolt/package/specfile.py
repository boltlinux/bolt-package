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
from lxml import etree
from com.nonterra.bolt.package.error import SpecfileError

class Specfile:

    RELAXNG_SCHEMA_SEARCH_PATH = [
        os.path.normpath(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "..", "..", "..", "..", "..", "relaxng", "package.rng.xml"
            )
        ),
        os.path.join(os.sep, "usr", "share", "bolt-pack", "package.rng.xml"),
        os.path.join(os.sep, "tools", "share", "bolt-pack", "package.rng.xml"),
    ]

    def __init__(self, filename):
        if not os.path.exists(filename):
            raise SpecfileError("no such file '%s'." % filename)

        parser = etree.XMLParser(encoding="utf-8", load_dtd=True,
                no_network=True, ns_clean=True, strip_cdata=True,
                resolve_entities=True)

        try:
            xml_doc = etree.parse(filename, parser)
            xml_doc.xinclude()
        except etree.XMLSyntaxError as e:
            raise SpecfileError(str(e))

        self.validate_structure(xml_doc)
        self.validate_format(xml_doc)

        self.xml_doc = xml_doc
    #end function

    def validate_structure(self, xml_doc):
        for path in Specfile.RELAXNG_SCHEMA_SEARCH_PATH:
            if os.path.exists(path):
                relaxng = etree.RelaxNG(file=path)
        #end for

        if not relaxng.validate(xml_doc):
            errors = []
            for err in relaxng.error_log:
                errors.append("* %s on line %d, column %d: %s" % 
                        (os.path.basename(err.filename), err.line,
                            err.column, err.message))
            #end for
            msg = "RELAX NG validation failed:\n" + "\n".join(errors)
            raise SpecfileError(msg)
        #end if

        return True
    #end function

    def validate_format(self, xml_doc):
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
            for attr in xml_doc.xpath(xpath):
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
            raise SpecfileError(msg)
        #end if

        return True
    #end function

#end class
