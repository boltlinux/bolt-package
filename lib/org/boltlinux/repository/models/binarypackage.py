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

class BinaryPackage(db.Model):
    __tablename__ = "binary_package"

    id_ = db.Column(db.Integer, primary_key=True, index=True)

    source_package_id = db.Column(db.Integer, db.ForeignKey("source_package.id_"),
            nullable=False, index=True)

    repo_name  = db.Column(db.String(50), nullable=False)
    libc       = db.Column(db.String(10), nullable=False)
    arch       = db.Column(db.String(10), nullable=False)
    name       = db.Column(db.String(50), nullable=False)
    version    = db.Column(db.String(50), nullable=False)
    component  = db.Column(db.String(10), nullable=False, index=True)
    filename   = db.Column(db.Text,       nullable=False)
    arch_indep = db.Column(db.Boolean(),  nullable=False, default=False)
    sortkey    = db.Column(db.Integer,    nullable=False, default=0)
    needs_scan = db.Column(db.Boolean(),  nullable=False, default=True)
    summary    = db.Column(db.Text(),     nullable=False)

    __table_args__ = (
        db.Index("ix_binary_package_repo_name_name_version",
                    "repo_name", "name", "version"),
        db.Index("ix_binary_package_repo_name_libc_arch_name_version",
                    "repo_name", "libc", "arch", "name", "version"),
        db.UniqueConstraint("repo_name", "libc", "arch", "name", "version")
    )
#end class

