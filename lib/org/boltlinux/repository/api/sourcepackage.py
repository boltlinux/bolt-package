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

from sqlalchemy.orm import exc as sql_exc
from werkzeug import exceptions as http_exc
from flask_restful import Resource, fields, marshal_with, abort
from org.boltlinux.repository.flaskinit import app, db
from org.boltlinux.repository.models import SourcePackage as SourcePackageModel

class SourcePackage(Resource):

    RESOURCE_FIELDS = {
        "name":             fields.String,
        "version":          fields.String,
        "upstream_version": fields.String,
        "status":           fields.Integer
    }

    @marshal_with(RESOURCE_FIELDS)
    def get(self, id_=None):
        if id_ is not None:
            try:
                return SourcePackageModel.query\
                    .filter_by(id_=id_)\
                    .one()
            except sql_exc.NoResultFound:
                raise http_exc.NotFound()
        #end if

        with app.app_context():
            s1 = db.aliased(SourcePackageModel)
            s2 = db.aliased(SourcePackageModel)

            subquery = db.session.query(db.func.max(s1.sortkey))\
                    .filter_by(name = s2.name)

            query = db.session.query(s2)\
                    .options(db.defer("xml"))\
                    .filter_by(sortkey=subquery)\
                    .order_by(s2.name)

            return query.all()
        #end with
    #end function

#end class

