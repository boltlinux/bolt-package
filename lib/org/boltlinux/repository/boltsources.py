# -*- encoding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2016 Tobias Koch <tobias.koch@gmail.com>
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
import sys
import subprocess
import logging

from lxml import etree
from org.boltlinux.package.appconfig import AppConfig
from org.boltlinux.package.specfile import Specfile
from org.boltlinux.repository.flaskapp import app, db
from org.boltlinux.repository.models import SourcePackage, UpstreamSource
from org.boltlinux.repository.packagerules import PackageRules
from org.boltlinux.error import MalformedSpecfile, RepositoryError
from org.boltlinux.package.xpkg import BaseXpkg

class BoltSources:

    def __init__(self, config, verbose=True):
        self._verbose      = verbose
        self._repositories = config.get("repositories", [])

        self._cache_dir = \
            config.get("cache-dir",
                os.path.realpath(
                    os.path.join(
                        AppConfig.get_config_folder(),
                        "cache", "pkg-rules"
                    )
                )
            )

        self.log = logging.getLogger("org.boltlinux.repository")
    #end function

    def refresh(self):
        for repo_info in self._repositories:
            if self._verbose:
                self.log.info(
                    "Refreshing Bolt package rules for repository '%s'."
                        % repo_info["name"])
            #end if

            rules = PackageRules(repo_info["name"], repo_info["rules"],
                    cache_dir=self._cache_dir)

            try:
                rules.refresh()
            except RepositoryError as e:
                self.log.error("Error refreshing packages rules for '%s': %s"
                        % (repo_info["name"], str(e)))
            #end try
        #end for
    #end function

    def update_db(self):
        source_pkg_index   = {}
        upstream_src_index = {}

        with app.app_context():
            for obj in SourcePackage.query.all():
                source_pkg_index \
                        .setdefault(obj.name, {}) \
                        .setdefault(obj.version, obj)
            #end for

            for obj in UpstreamSource.query.all():
                upstream_src_index[obj.name] = obj

            for repo_info in self._repositories:
                if self._verbose:
                    self.log.info(
                        "Updating DB entries for Bolt repository '%s'."
                            % repo_info["name"])
                #end if

                rules = PackageRules(repo_info["name"], repo_info["rules"],
                        cache_dir=self._cache_dir)

                self._parse_revisions(rules, source_pkg_index,
                        upstream_src_index)
            #end for

            db.session.commit()
        #end with
    #end function

    # PRIVATE

    def _parse_revisions(self, rules, source_pkg_index, upstream_src_index):
        for revision in rules.revisions():
            revision.checkout()

            for package_xml in revision.rules():
                try:
                    specfile = Specfile(package_xml)
                except MalformedSpecfile as e:
                    short_path = package_xml[len(rules._cache_dir):]\
                            .lstrip("/")
                    self.log.warning("Malformed specfile '%s'." % short_path)
                    continue
                #end try

                source_name      = specfile.source_name
                version          = specfile.latest_version
                upstream_version = specfile.upstream_version
                packages         = specfile.binary_packages

                xml = etree.tostring(specfile.xml_doc,
                        pretty_print=True, encoding="unicode")

                ref_obj = source_pkg_index \
                        .get(source_name, {})\
                        .get(version)

                if ref_obj is not None:
                    self.log.warning(
                        "Package '%s' at '%.8s' in '%s' modified without version bump." %
                            (source_name, revision._commit_id, rules._repo_name)
                    )
                    ref_obj.xml = xml
                    ref_obj.upstream_version = upstream_version
                else:
                    ref_obj = SourcePackage(
                        name             = source_name,
                        version          = version,
                        upstream_version = upstream_version,
                        xml              = xml
                    )
                    db.session.add(ref_obj)

                    source_pkg_index \
                            .setdefault(source_name, {})\
                            .setdefault(version, ref_obj)
                #end if

                upstream_ref_obj = upstream_src_index.get(source_name)

                if upstream_version:
                    if upstream_ref_obj:
                        ref_obj.upstream_source_id = upstream_ref_obj.id_

                        comp = BaseXpkg.compare_versions(upstream_version,
                                upstream_ref_obj.version)

                        if comp < 0:
                            ref_obj.status = SourcePackage.STATUS_BEHIND
                        elif comp > 0:
                            ref_obj.status = SourcePackage.STATUS_AHEAD
                        else:
                            ref_obj.status = SourcePackage.STATUS_CURRENT
                    else:
                        self.log.warning(
                            "Package '%s' has no upstream reference." %
                                source_name
                        )
                    #end if
                elif upstream_ref_obj:
                    self.log.warning(
                        "Package '%s' does not track upstream source." %
                            source_name
                    )
                #end if
            #end for
        #end for
    #end function

#end class

