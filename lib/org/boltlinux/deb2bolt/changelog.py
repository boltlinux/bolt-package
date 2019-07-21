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

from datetime import datetime
from dateutil.tz import tzlocal
from dateutil.parser import parse as parse_datetime
from xml.sax.saxutils import escape as xml_escape

class Change:

    def __init__(self, desc):
        self.desc = desc

    def as_xml(self, indent=0):
        buf = "<li>" + xml_escape(self.desc) + "</li>"
        return re.sub(r"^", " " * 4 * indent, buf) + "\n"
    #end function

#end class

class ChangeSet:

    def __init__(self, content, contributor=None):
        self._parse_content(content)
        self.contributor = contributor
    #end function

    def _parse_content(self, content):
        changes = []
        lines   = []

        for line in content.splitlines():
            if not line.strip():
                continue

            m = re.match(r"^(\s*)(\*|-)(.*)$", line)
            if not m:
                lines.append(line.strip())
                continue
            if lines:
                changes.append(Change(" ".join(lines)))
                lines = []

            lines.append(m.group(3).strip())
        #end for

        if lines:
            changes.append(Change(" ".join(lines)))

        self.changes = changes
    #end function

    def as_xml(self, indent=0):
        if self.contributor:
            buf = '<changeset contributor="%s">\n' % self.contributor
        else:
            buf = '<changeset>\n'
        for change in self.changes:
            buf += change.as_xml(indent=1)
        buf += '</changeset>'
        return re.sub(r"^", " " * 4 * indent, buf, flags=re.M) + "\n"
    #end function

#end class

class Release:

    def __init__(self, version, content, maintainer, email, date):
        m = re.match(
            r"^(?:(\d+):)?([-+:~.a-zA-Z0-9]+?)(?:-([^-]+))?$",
            version
        )

        self.epoch, self.version, self.revision = \
                m.groups(default="") if m else ("", "", "")

        if not self.revision:
            self.revision = "0"

        self.upstream_version = version
        self.maintainer = maintainer
        self.email = email
        self.date = date

        self._parse_content(content)
    #end function

    def _parse_content(self, content):
        contributor = None
        changesets  = []
        tmp_content = ""

        for line in content.splitlines(True):
            if not line.strip():
                if tmp_content:
                    changesets.append(ChangeSet(tmp_content, contributor))
                    tmp_content = ""
                    contributor = None
                #end if
                continue
            #end if

            m = re.match(r"^\s*\[(.*?)\]\s*", line)
            if m:
                contributor = m.group(1).strip()
                continue
            #end if

            tmp_content += line
        #end for

        if tmp_content:
            changesets.append(ChangeSet(tmp_content, contributor))

        self.changesets = changesets
    #end function

    def as_xml(self, indent=0, have_upstream_version=False):
        if self.epoch:
            epoch = ' epoch="%s"' % self.epoch
        else:
            epoch = ''

        info_set = {
            "epoch":      epoch,
            "version":    self.version,
            "revision":   self.revision,
            "upstream":   self.upstream_version,
            "maintainer": self.maintainer,
            "email":      self.email,
            "date":       self.date
        }

        buf  = '<release%(epoch)s version="%(version)s" revision="%(revision)s"'  # noqa:
        if have_upstream_version:
            buf += ' upstream-version="%(upstream)s"\n'
        else:
            buf += '\n'
        buf += '    maintainer="%(maintainer)s" email="%(email)s"\n'
        buf += '    date="%(date)s">\n'
        buf  = buf % info_set
        for chset in self.changesets:
            buf += chset.as_xml(indent=1)
        buf += '</release>'

        return re.sub(r"^", " " * 4 * indent, buf, flags=re.M) + "\n"
    #end function

#end class

class Changelog:

    def __init__(self, filename):
        self.releases = []

        version = None
        content = ""
        email   = ""
        date    = None

        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                m = re.match(
                    r"^\s*[-.a-z0-9]+\s+\(([^)]+)\)(?:\s+(?:\w|-)+)+;"
                    r"\s*urgency=\w+", line
                )
                if m:
                    version = m.group(1)
                    content = ""
                    continue
                #end if

                m = re.match(
                    r"^\s* --\s+([^<]+)\s+<([^>]+)>\s+"
                    r"((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), .*$)", line
                )
                if m:
                    maintainer = m.group(1)
                    email      = m.group(2)
                    date       = parse_datetime(m.group(3))
                    content    = content.strip()

                    self.releases.append(
                        Release(
                            version,
                            content,
                            maintainer,
                            email,
                            date
                        )
                    )
                    continue
                #end if

                content += line
            #end for
        #end with
    #end function

    def to_xml(self, indent=0, maintainer_info=None):
        buf  = '<?xml version="1.0" encoding="utf-8"?>\n'
        buf += '<changelog>\n'

        if maintainer_info is not None:
            version    = self.releases[0].upstream_version
            maintainer = maintainer_info.get("name", "")
            email      = maintainer_info.get("email", "")
            date       = datetime.now(tzlocal()).replace(microsecond=0)
            content    = "* Adaptation of Debian sources for Bolt OS"

            release = Release(version, content, maintainer, email, date)
            release.revision += "bolt1"

            buf += release.as_xml(indent=1, have_upstream_version=True)
        else:
            for rel in self.releases:
                buf += rel.as_xml(indent=1)

        buf += '</changelog>'
        return re.sub(r"^", " " * 4 * indent, buf, flags=re.M) + "\n"
    #end function

#end class
