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

import re
from xml.sax.saxutils import escape as xml_escape

class BasePackage:

    def __init__(self):
        self.fields = {}

    def get(self, key, default=None):
        return self.fields.get(key, default)

    def parse_content(self, content):
        field_name  = None
        field_value = None

        ######################################################################
        # Parse block of meta data.

        fields = {}

        for line in content.splitlines():
            if not line.strip() or line.startswith("#"):
                continue

            if re.match(r"^\S+:", line):
                field_name, field_value = line.split(":", 1)

                field_name = field_name\
                    .strip()\
                    .lower()
                field_value = field_value.strip()

                fields[field_name] = field_value

                if field_name in ["source", "package"]:
                    fields["name"] = field_value
            else:
                fields[field_name] += "\n" + line
            #end if
        #end for

        ######################################################################
        # Lots of twisted substitutions and transforms on dep fields.

        dependency_types = [
            "pre-depends", "depends",  "build-depends",
            "suggests",    "provides", "breaks",
            "conflicts",   "replaces", "build-conflicts"
        ]

        for dep_type in dependency_types:
            if fields.get(dep_type):
                val = fields[dep_type]
                val = re.sub(r"\s+", "", val)
                val = re.sub(r"\[[^\]]+\]", "", val)
                val = re.sub(r"(\([<=>]+)", r"\1 ", val)
                val = re.sub(r"= \$\{binary:Version\}", "==", val)
                val = re.sub(r"= \$\{source:Version\}", "==", val)
                val = re.sub(r"", "", val)
                val = val.split(",")
                val = filter(lambda x: not x.startswith("$"), val)
                val = filter(lambda x: x, val)
                val = map(lambda x: re.match(r"([^(]+)(?:\(([^)]+)\))?", x)\
                        .groups(default=""), val)
                val = map(lambda x: (x[0].split("|")[0] \
                        if "|" in x[0] else x[0], x[1]), val)
                val = map(lambda x: (re.sub(r"<!?stage\d+>$", "", x[0]), x[1]),
                        val)
                fields[dep_type] = list(val)
            else:
                fields[dep_type] = []
            #end if
        #end for

        ######################################################################
        # Turn package description into crude XML.

        if "description" in fields:
            if "\n" in fields["description"]:
                summary, desc = re.split(r"\n", fields["description"], 1)
            else:
                summary, desc = fields["description"], ""
            #end if
            summary, desc = summary.strip(), desc.strip()
            summary, desc = xml_escape(summary), xml_escape(desc)
            desc = re.sub(r"^(\s+)\.\s*$", r"</p>\n<p>", desc, flags=re.M)
            desc = re.sub(r" +", r" ", desc)
            desc = re.sub(r"^\s*", r" " * 8, desc, flags=re.M)
            fields["summary"], fields["description"] = summary, desc
        #end if

        self.fields = fields
    #end function

#end class
