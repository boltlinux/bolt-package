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
from marshmallow import Schema, fields, validates, post_load, ValidationError

class RequestArgsSchema(Schema):
    letter = fields.String()
    search = fields.String()
    libc   = fields.String()
    arch   = fields.String()
    offkey = fields.String()
    items  = fields.Integer()

    @validates("letter")
    def validate_letter(self, letter):
        if ord(letter) < 97 or ord(letter) < 122:
            raise ValidationError("Letter is out of supported range [a-z]")

    @validates("search")
    def validate_search(self, search):
        if re.match(r"^[-a-zA-Z0-9.+]*$", search) is None:
            raise ValidationError("Invalid characters in search term.")

    @validates("libc")
    def validate_libc(self, libc):
        if libc not in ["musl", "glibc"]:
            raise ValidationError("Unknown libc name.")

    @validates("offkey")
    def validate_offkey(self, offkey):
        if re.match(r"^[-a-zA-Z0-9.+]+$", offkey) is None:
            raise ValidationError("Invalid key offset.")

    @validates("items")
    def validate_items(self, items):
        if items > 200:
            raise ValidationError("You may request a maximum of 200 items.")
        if items < 0:
            raise ValidationError("Cannot return a negative number of items.")

    @post_load
    def setdefaults(self, data):
        data.setdefault("items", 10)

        for key in ["offkey", "search"]:
            if key in data:
                data[key] = data[key].lower()
        #end for

        return data
    #end function

#end class
