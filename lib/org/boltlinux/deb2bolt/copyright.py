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
import logging
import textwrap

from xml.sax.saxutils import escape as xml_escape
from org.boltlinux.error import BoltError

LOGGER = logging.getLogger(__name__)

class CopyrightInfo:

    class FormattingError(RuntimeError):
        pass

    def __init__(self, filename=None):
        self._metadata = []
        self._licenses = {}

        if filename:
            self.read(filename)
    #end function

    def read(self, filename):
        self._metadata.clear()
        self._licenses.clear()

        has_copyright_format = True
        with open(filename, "r", encoding="utf-8") as f:
            header = next(f)

        try:
            key, value = [item.strip() for item in header.split(":", 1)]
            if key.lower() != "format":
                has_copyright_format = False
        except ValueError:
            has_copyright_format = False

        if has_copyright_format:
            with open(filename, "r", encoding="utf-8") as f:
                enumerated_lines = enumerate(f, start=1)

                blocks  = []
                current = []

                for lineno, line in enumerated_lines:
                    if line.strip():
                        current.append(
                            (lineno, line)
                        )
                    elif current:
                        blocks.append(current)
                        current = []
                    #end if
                #end for

                if current:
                    blocks.append(current)
            #end with

            blocks.pop(0)

            try:
                self._metadata, self._licenses = \
                    self._parse_and_filter_blocks(blocks)
            except CopyrightInfo.FormattingError as e:
                LOGGER.warning(str(e))
                has_copyright_format = False
        #end if

        if not has_copyright_format:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()

            self._metadata = [
                {
                    "files": ["*"],
                    "license": "custom",
                    "_license_text": content
                }
            ]
        #end if
    #end function

    def to_xml(self):
        result = '<copyright>\n'

        for meta in self._metadata:
            result += '    <files license="{}">\n'.format(
                xml_escape(meta["license"])
            )

            for file_ in meta["files"]:
                result += '        <file src="{}"/>\n'.format(
                    xml_escape(file_)
                )
            #end for

            if "copyright" in meta:
                copyright = re.sub(
                    r"^\s*", "", meta["copyright"], flags=re.M
                ).strip() + "\n"

                result += '        <copyright-notice><![CDATA[\n'
                result += copyright
                result += '        ]]></copyright-notice>\n'
            #end if

            if "_license_text" in meta:
                license = meta["_license_text"].strip() + "\n"

                result += '        <license><![CDATA[\n'
                result += license
                result += '        ]]></license>\n'
            #end if

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

            files = meta.get("files")

            if files:
                metadata.append(meta)
            else:
                if files is not None:
                    continue

                license = meta.get("license")
                if license is None:
                    continue

                licenses[license] = meta["_license_text"]
            #end if
        #end for

        return metadata, licenses
    #end function

    def _parse_block(self, block):
        key  = ""
        meta = {}

        for lineno, line in block:
            if line.startswith("#"):
                continue
            if not line.strip():
                break

            m = re.match(r"^(?P<key>\S+):(?P<val>.*\n?)$", line)
            if m:
                key = m.group("key").lower()
                val = m.group("val")
                if val:
                    meta[key] = val
            else:
                if not key:
                    raise CopyrightInfo.FormattingError(
                        "formatting error in \"debian/copyright\" on line '{}'"
                        .format(lineno)
                    )
                #end if
                meta[key] += line
            #end if
        #end for

        return self._postprocess_fields(meta)
    #end function

    def _postprocess_fields(self, meta):
        for key in list(meta.keys()):
            if key in ["license"]:
                val = meta[key].strip()

                if "\n" in val:
                    summary, text = val.split("\n", 1)
                    meta[key] = summary.strip()
                    meta["_license_text"] = self._postprocess_license_text(text)
                else:
                    meta[key] = val
            elif key in ["files"]:
                meta[key] = list(
                    filter(
                        lambda x: not x.startswith("debian/"),
                        meta[key].strip().split()
                    )
                )
            elif key in ["copyright"]:
                pass
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
