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

from org.boltlinux.repository.flaskinit import db

class PackageEntry(db.Model):
    __tablename__ = "package_entry"

    id_ = db.Column(db.Integer, primary_key=True, index=True)

    binary_package_id = db.Column(
        db.Integer,
        db.ForeignKey("binary_package.id_"),
        nullable=False,
        index=True
    )

    uname    = db.Column(db.String(64),  nullable=False)
    gname    = db.Column(db.String(64),  nullable=False)
    mode     = db.Column(db.Integer,     nullable=False)
    pathname = db.Column(db.String(256), nullable=False, index=True)
    target   = db.Column(db.String(256), nullable=True, default=None)
#end class
