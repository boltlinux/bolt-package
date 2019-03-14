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

class SourcePackage(db.Model):
    __tablename__ = "source_package"

    STATUS_UNKNOWN = 0
    STATUS_BEHIND  = 1
    STATUS_CURRENT = 2
    STATUS_AHEAD   = 3

    id_ = db.Column(db.Integer, primary_key=True, index=True)

    upstream_source_id = db.Column(db.Integer,
            db.ForeignKey("upstream_source.id_"), nullable=True, index=True)

    repo_name        = db.Column(db.String(50), nullable=False)
    name             = db.Column(db.String(50), nullable=False)
    version          = db.Column(db.String(50), nullable=False)
    upstream_version = db.Column(db.String(50), nullable=True)
    git_hash         = db.Column(db.String(8),  nullable=True)
    sortkey          = db.Column(db.Integer,    nullable=False, default=0)
    status           = db.Column(db.Integer,    nullable=False,
                                 default=STATUS_UNKNOWN, index=True)
    summary          = db.Column(db.Text(),     nullable=False)

    json = db.Column(db.Text)

    __table_args__ = (
        db.Index("ix_source_package_repo_name_name_version",
                    "repo_name", "name", "version"),
        db.UniqueConstraint("repo_name", "name", "version")
    )
#end class

