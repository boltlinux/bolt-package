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

from flask import request
from sqlalchemy.orm import exc as sql_exc
from werkzeug import exceptions as http_exc
from flask_restful import Resource, fields, marshal_with

from org.boltlinux.repository.flaskinit import app, db
from org.boltlinux.repository.models import BinaryPackage as BinaryPackageModel
from org.boltlinux.repository.api.schema import RequestArgsSchema

class BinaryPackage(Resource):

    RESOURCE_FIELDS = {
        "name":       fields.String,
        "version":    fields.String,
        "component":  fields.String,
        "arch":       fields.String,
        "libc":       fields.String,
        "arch_indep": fields.Boolean
    }

    @marshal_with(RESOURCE_FIELDS)
    def get(self, id_=None, version=None):
        if id_ is not None:
            return self._get_one(id_, version)
        else:
            return self._get_many()
        #end if
    #end function

    def _get_one(self, id_, version):
        if isinstance(id_, int):
            query = BinaryPackageModel.query\
                .filter_by(id_=id_)
        else:
            query = BinaryPackageModel.query\
                .filter_by(name=id_)\

            if version:
                query = query.filter_by(version=version)

            query = query\
                .order_by(BinaryPackageModel.sortkey.desc())\
                .limit(1)
        #end if

        try:
            return query.one()
        except sql_exc.NoResultFound:
            raise http_exc.NotFound()
    #end function

    def _get_many(self):
        req_args, errors = RequestArgsSchema().load(request.args)
        if errors:
            raise http_exc.BadRequest(errors)

        offkey = req_args.get("offkey", "")
        items  = req_args.get("items",  10)
        search = req_args.get("search", None)
        libc   = req_args.get("libc",   "musl")
        arch   = req_args.get("arch", "x86_64")

        s1 = db.aliased(BinaryPackageModel)
        s2 = db.aliased(BinaryPackageModel)

        subquery = db.session.query(db.func.max(s1.sortkey))\
                .filter_by(name = s2.name)

        query = db.session.query(s2)\
                .filter(s2.name > offkey)\
                .filter_by(libc=libc)\
                .filter_by(arch=arch)\
                .filter_by(sortkey=subquery)\
                .order_by(s2.name)

        if search:
            query = query.filter(s2.name.like("%"+search+"%"))

        query = query.limit(items)

        return query.all()
    #end function

#end class

