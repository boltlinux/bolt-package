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
import subprocess

from dateutil.parser import parse as parse_datetime

from org.boltlinux.error import BoltValueError

class InReleaseFile:

    def __init__(self, contents):
        if not contents.startswith("-----BEGIN PGP SIGNED MESSAGE-----"):
            raise BoltValueError("invalid contents for InRelease file.")

        self.contents = contents

        self.date = None
        self.dict = {}

        for line in contents.splitlines():
            if line.startswith("-----BEGIN PGP SIGNATURE-----"):
                break

            if self.date is None and line.startswith("Date:"):
                self.date = parse_datetime(line.split(":", 1)[-1].strip())

            m = re.match(
                r"""^
                \s+(?P<hash>[0-9a-f]{64})
                \s+(?P<size>\d+)
                \s+(?P<filename>\S+)
                \s*$
                """,
                line,
                flags=re.VERBOSE
            )

            if m:
                self.dict[m.group("filename")] = m.group("hash")
        #end for
    #end function

    @classmethod
    def load(cls, filename):
        with open(filename, "r", encoding="utf-8") as f:
            return InReleaseFile(f.read())

    def hash_for_filename(self, filename):
        return self.dict[filename]

    def by_hash_path(self, filename):
        return os.path.join(
            os.path.dirname(filename),
            "by-hash", "SHA256",
            self.hash_for_filename(filename)
        )

    def valid_signature(self, keyring=None):
        command = ["gpg", "--verify"]
        if keyring:
            command.extend([
                "--no-default-keyring",
                "--keyring", keyring
            ])
        #end if

        proc = subprocess.run(
            command,
            input=self.contents,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        return proc.returncode == 0
    #end function

#end class
