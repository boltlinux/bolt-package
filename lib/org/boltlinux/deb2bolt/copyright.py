# -*- encoding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2019 Tobias Koch <tobias.koch@gmail.com>
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
import textwrap

from xml.sax.saxutils import escape as xml_escape
from org.boltlinux.error import BoltError

class CopyrightInfo:

    def __init__(self):
        self._metadata = []
        self._licenses = {}

    def read(self, filename):
        self._metadata.clear()
        self._licenses.clear()

        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()

        content = content.strip()
        content = re.sub(r"^\s*\n$", r"\n", content, flags=re.M)
        blocks  = re.split(r"\n\n+", content)

        self._metadata, self._licenses = self._parse_and_filter_blocks(blocks)
    #end function

    def to_xml(self):
        result = '<copyright>\n'

        for meta in self._metadata:
            result += '    <files license="{}">\n'.format(
                xml_escape(meta["License"])
            )

            for file_ in meta["Files"]:
                result += '        <file src="{}"/>\n'.format(
                    xml_escape(file_)
                )

            result += '    </files>\n'
        #end for

        for id_, text in self._licenses.items():
            result += '    <license handle="{}"><![CDATA[\n'.format(id_)
            result += text
            result += '    ]]></license>\n'
        #end for

        result += '</copyright>\n'

        return result
    #end function

    # PRIVATE

    def _parse_and_filter_blocks(self, blocks):
        metadata = []
        licenses = {}

        for block in blocks:
            meta = self._parse_block(block)
            if not meta:
                continue

            files = meta.get("Files")

            if not files:
                if files is not None:
                    continue

                license = meta.get("License")

                if license is None:
                    continue

                licenses[license] = meta["LicenseText"]
            else:
                if "LicenseText" in meta:
                    licenses[meta["License"]] = meta["LicenseText"]
                    del meta["LicenseText"]
                #end if

                metadata.append(meta)
            #end if
        #end for

        return metadata, licenses
    #end function

    def _parse_block(self, block):
        key  = ""
        meta = {}

        for lineno, line in enumerate(block.splitlines(True)):
            if line.startswith("#"):
                continue
            if not line.strip():
                break

            m = re.match(r"^(?P<key>\S+):(?P<val>.*\n?)$", line)
            if m:
                key = m.group("key")
                val = m.group("val")
                if val:
                    meta[key] = val
            else:
                if not key:
                    raise BoltError(
                        "formatting error on line '{}'".format(lineno)
                    )
                #end if
                meta[key] += line
            #end if
        #end for

        return self._postprocess_fields(meta)
    #end function

    def _postprocess_fields(self, meta):
        for key in list(meta.keys()):
            if key in ["License"]:
                val = meta[key].strip()

                if "\n" in meta[key]:
                    summary, text = val.split("\n", 1)
                    meta[key] = summary.strip()
                    meta["LicenseText"] = self._postprocess_license_text(text)
                else:
                    meta[key] = val.strip()
                #end if
            elif key in ["Files"]:
                meta[key] = list(
                    filter(
                        lambda x: not x.startswith("debian/"),
                        meta[key].strip().split()
                    )
                )
            else:
                meta[key] = re.sub(r"\s+", " ", meta[key].strip(), flags=re.M)
            #end if
        #end for

        return meta
    #end function

    def _postprocess_license_text(self, text):
        text = textwrap.dedent(text)
        text = re.sub(r"^\s*\.\s*$", r"", text, flags=re.M)
        text = text.rstrip() + "\n"

        return text
    #end function

#end class
