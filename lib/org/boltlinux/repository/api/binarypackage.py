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
from werkzeug import exceptions as http_exc
from flask_restful import Resource, fields, marshal, marshal_with

from org.boltlinux.repository.flaskinit import db
from org.boltlinux.repository.models import \
    BinaryPackage as BinaryPackageModel, \
    SourcePackage as SourcePackageModel
from org.boltlinux.repository.api.schema import RequestArgsSchema

class BinaryPackage(Resource):

    RESOURCE_FIELDS = {
        "id_":        fields.Integer,
        "repo_name":  fields.String,
        "name":       fields.String,
        "version":    fields.String,
        "component":  fields.String,
        "arch":       fields.String,
        "libc":       fields.String,
        "arch_indep": fields.Boolean,
        "summary":    fields.String
    }

    def get(self, repo="core", libc="musl", arch="x86_64",
            name=None, version=None):
        if repo:
            if name:
                return self._get_one(repo, name, version)
            else:
                return self._get_many(repo, arch, libc)
        #end if
    #end function

    def _get_one(self, repo, name, version):
        ######################################################################
        #
        # Fetch all combinations of arch, libc for package, version.
        #
        ######################################################################

        if version:
            package_list = BinaryPackageModel.query\
                .filter_by(repo_name=repo)\
                .filter_by(name=name)\
                .filter_by(version=version)\
                .all()
        else:
            s1 = db.aliased(BinaryPackageModel)
            s2 = db.aliased(BinaryPackageModel)

            subquery = db.session.query(db.func.max(s1.sortkey))\
                .filter_by(repo_name=repo)\
                .filter_by(libc=s2.libc)\
                .filter_by(arch=s2.arch)\
                .filter_by(name=s2.name)

            package_list = db.session.query(s2)\
                .filter_by(repo_name=repo)\
                .filter_by(name=name)\
                .filter_by(sortkey=subquery)\
                .all()
        #end if

        if not package_list:
            raise http_exc.NotFound("Package '{}' version '{}' not found."
                    .format(name, version))

        # Use the first entry as the one to display.
        bin_pkg = package_list[0]
        obj = marshal(bin_pkg, BinaryPackage.RESOURCE_FIELDS)

        obj["variants"] = {}

        for pkg in package_list:
            obj["variants"]\
                .setdefault(pkg.arch, {})\
                .setdefault(pkg.libc, pkg.version)
        #end for

        ######################################################################
        #
        # Fetch the source package matching the binary package and extract the
        # binary package description.
        #
        ######################################################################

        source_pkg = SourcePackageModel.query.get(bin_pkg.source_package_id)

        obj["data"] = {}

        if source_pkg:
            source_info = json.loads(source_pkg.json)
            for pkg in source_info["packages"]:
                if pkg["name"] == name:
                    obj["data"] = pkg
                    break
            #end for
        #end if

        ######################################################################
        #
        # Fetch all versions of package.
        #
        ######################################################################

        obj["versions"] = [
            r for (r,) in db.session\
                .query(BinaryPackageModel.version)\
                .filter_by(repo_name=repo)\
                .filter_by(name=name)\
                .distinct()
        ]

        ######################################################################
        #
        # Replace '==' version specifiers with package version.
        #
        ######################################################################

        for entry in obj["data"].get("requires", []):
            version_spec = entry.get("version", "").strip()
            if version_spec.endswith("=="):
                entry["version"] = "{} {}".format(version_spec[:-1],
                        obj["version"])

        return obj
    #end function

    @marshal_with(RESOURCE_FIELDS)
    def _get_many(self, repo, arch, libc):
        req_args, errors = RequestArgsSchema().load(request.args)
        if errors:
            raise http_exc.BadRequest(errors)

        offkey = req_args.get("offkey", "")
        items  = req_args.get("items",  20)
        search = req_args.get("search", None)
        libc   = req_args.get("libc",   libc)
        arch   = req_args.get("arch",   arch)

        s1 = db.aliased(BinaryPackageModel)
        s2 = db.aliased(BinaryPackageModel)

        subquery = db.session.query(db.func.max(s1.sortkey))\
                .filter_by(repo_name=repo)\
                .filter_by(libc=libc)\
                .filter_by(arch=arch)\
                .filter_by(name=s2.name)

        query = db.session.query(s2)\
                .filter_by(repo_name=repo)\
                .filter(s2.name > offkey)\
                .filter_by(libc=libc)\
                .filter_by(arch=arch)\
                .order_by(s2.name)

        if search:
            query = query.filter(s2.name.like("%"+search+"%"))

        return query\
                .filter_by(sortkey=subquery)\
                .limit(items)\
                .all()
    #end function

#end class

