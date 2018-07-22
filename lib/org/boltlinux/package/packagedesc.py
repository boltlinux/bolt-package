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
from lxml import etree

class PackageDescription:

    INLINE_ELEMENTS_STYLE = """\
<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="em">
    <xsl:text>|</xsl:text><xsl:apply-templates/><xsl:text>|</xsl:text>
  </xsl:template>

  <xsl:template match="*|text()|comment()">
    <xsl:copy>
      <xsl:copy-of select="@*"/>
      <xsl:apply-templates/>
    </xsl:copy>
  </xsl:template>

</xsl:stylesheet>
"""

    BLOCK_ELEMENTS_STYLE = """\
<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:bolt="http://schema.boltlinux.org/2011/XSL/BoltPack"
  extension-element-prefixes="bolt">

  <xsl:output method="text" omit-xml-declaration="yes" encoding="UTF-8"/>

  <xsl:template match="description">
      <xsl:apply-templates/>
  </xsl:template>

  <xsl:template match="p">
    <xsl:value-of select="bolt:block_format(.)"/>
    <xsl:if test="following-sibling::*">
      <xsl:text>&#x0a; .&#x0a;</xsl:text>
    </xsl:if>
  </xsl:template>

  <xsl:template match="ul">
    <xsl:apply-templates/>
    <xsl:if test="following-sibling::*">
      <xsl:text>&#x0a; .&#x0a;</xsl:text>
    </xsl:if>
  </xsl:template>

  <xsl:template match="li">
    <xsl:value-of select="bolt:block_format(.)"/>
    <xsl:if test="following-sibling::*">
      <xsl:text>&#x0a;</xsl:text>
    </xsl:if>
  </xsl:template>

  <xsl:template match="node()|comment()"/>

</xsl:stylesheet>
"""

    def __init__(self, xml_input):
        if isinstance(xml_input, etree._Element):
            self.desc_node = xml_input
        elif isinstance(xml_input, str):
            self.desc_node = etree.fromstring(xml_input)
        else:
            msg = "expected 'etree._Element' or 'str' but got '%s'" % \
                    xml_input.__class__.__name__
            raise ValueError(msg)
        #end if
    #end function

    def summary(self):
        summary_text = etree.tostring(self.desc_node.xpath("summary")[0],
                method="text", encoding="unicode")
        return PackageDescription.normalize_space(summary_text)
    #end function

    def full_description(self):
        ns_uri = "http://schema.boltlinux.org/2011/XSL/BoltPack"
        ns = etree.FunctionNamespace(ns_uri)
        ns.prefix = "bolt"
        ns["block_format"] = PackageDescription.CustomXPath.block_format

        inline_elements_transform = etree.XSLT(
            etree.fromstring(
                PackageDescription.INLINE_ELEMENTS_STYLE
            )
        )

        block_elements_transform = etree.XSLT(
            etree.fromstring(
                PackageDescription.BLOCK_ELEMENTS_STYLE
            )
        )

        result = block_elements_transform(
            inline_elements_transform(self.desc_node)
        )

        return str(result)
    #end function

    @classmethod
    def normalize_space(klass, text):
        return re.sub(r"\s+", " ", text, flags=re.MULTILINE).strip()
    #end function

    class CustomXPath:

        @staticmethod
        def block_format(context, node):
            width = 80
            if node[0].tag == "li":
                indent = 3
            else:
                indent = 1
            #end if

            lines = []
            line  = " " * indent

            text = etree.tostring(node[0], method="text", encoding="unicode")
            for match in re.finditer(r"\S+", text):
                if len(line) + len(match.group(0)) > width:
                    if len(line.strip()) > 0:
                        lines.append(line)
                        line = " " * indent
                    #end if
                #end if

                line += match.group(0)
                if len(line) < width:
                    line += " "
            #end for

            if len(line.strip()) > 0:
                lines.append(line)

            result = "\n".join(lines)

            if node[0].tag == "li":
                result = list(result)
                result[1] = "*"
                result = "".join(result)
            #end if

            return result
        #end function

    #end class

#end class
