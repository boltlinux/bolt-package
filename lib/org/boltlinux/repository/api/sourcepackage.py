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

import json

from flask import request
from sqlalchemy.orm import exc as sql_exc
from werkzeug import exceptions as http_exc
from flask_restful import Resource, fields, marshal_with, marshal

from org.boltlinux.repository.flaskinit import db
from org.boltlinux.repository.models import SourcePackage as SourcePackageModel
from org.boltlinux.repository.api.schema import RequestArgsSchema

class SourcePackage(Resource):

    RESOURCE_FIELDS = {
        "id_":              fields.Integer,
        "repo_name":        fields.String,
        "name":             fields.String,
        "version":          fields.String,
        "upstream_version": fields.String,
        "status":           fields.Integer,
        "summary":          fields.String
    }

    def get(self, repo=None, name=None, version=None):
        if repo:
            if name and version:
                return self._get_one(repo, name, version)
            else:
                return self._get_many(repo)

            return None
    #end function

    def _get_one(self, repo, name, version):
        query = SourcePackageModel.query\
                .filter_by(repo_name=repo)\
                .filter_by(name=name)\
                .filter_by(version=version)

        try:
            result = query.one()
        except sql_exc.NoResultFound:
            raise http_exc.NotFound()

        obj = marshal(result, self.RESOURCE_FIELDS)
        obj["data"] = json.loads(result.json)

        return obj
    #end function

    @marshal_with(RESOURCE_FIELDS)
    def _get_many(self, repo=None):
        req_args, errors = RequestArgsSchema().load(request.args)
        if errors:
            raise http_exc.BadRequest(errors)

        offkey = req_args.get("offkey", "")
        items  = req_args.get("items",  10)
        search = req_args.get("search", None)

        s1 = db.aliased(SourcePackageModel)
        s2 = db.aliased(SourcePackageModel)

        subquery = db.session.query(db.func.max(s1.sortkey))\
                .filter_by(repo_name=repo)\
                .filter_by(name=s2.name)

        query = db.session.query(s2)\
                .options(db.defer("json"))\
                .filter(s2.name > offkey)\
                .filter_by(repo_name=repo)\
                .order_by(s2.name)

        if search:
            query = query.filter(s2.name.like("%"+search+"%"))

        return query\
                .filter_by(sortkey=subquery)\
                .limit(items)\
                .all()
    #end function

#end class

