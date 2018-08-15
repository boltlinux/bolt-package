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
import logging
import functools

from lxml import etree
from org.boltlinux.package.appconfig import AppConfig
from org.boltlinux.package.specfile import Specfile
from org.boltlinux.repository.flaskinit import app, db
from org.boltlinux.repository.models import SourcePackage, UpstreamSource, \
        Setting
from org.boltlinux.repository.boltpackagerules import BoltPackageRules
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
                    "Refreshing Bolt source package rules for origin '%s'."
                        % repo_info["name"])
            #end if

            rules = BoltPackageRules(repo_info["name"], repo_info["rules"],
                    cache_dir=self._cache_dir)

            try:
                rules.refresh()
            except RepositoryError as e:
                msg = "Error refreshing Bolt source packages rules for origin '%s': %s"
                self.log.error(msg % (repo_info["name"], str(e)))
            #end try
        #end for
    #end function

    def update_db(self):
        with app.app_context():
            source_pkg_index   = self._generate_source_pkg_index()
            upstream_src_index = self._generate_upstream_src_index()

            for repo_info in self._repositories:
                if self._verbose:
                    self.log.info(
                        "Updating Bolt source package DB entries for origin '%s'."
                            % repo_info["name"])
                #end if

                repo_name = repo_info["name"]

                start_rev = Setting.query\
                        .filter_by(name = "last_processed_revision@" + repo_name)\
                        .one_or_none()

                rules = BoltPackageRules(repo_name, repo_info["rules"],
                        cache_dir=self._cache_dir)

                self._parse_revisions(rules, source_pkg_index, upstream_src_index,
                        start_revision=start_rev and start_rev.value)

                if start_rev is not None:
                    start_rev.value = rules.get_head_hash()
                else:
                    start_rev = Setting(
                        name  = "last_processed_revision@" + repo_name,
                        value = rules.get_head_hash()
                    )

                    db.session.add(start_rev)
                #end function
            #end for

            # calculate the sortkeys for packages of same name
            self._sort_source_packages(source_pkg_index)

            # make sure all packages have their upstream ref set
            self._fix_upstream_refs(source_pkg_index, upstream_src_index)

            # mark packages as recent, up2date, outdated
            self._determine_recentness(source_pkg_index, upstream_src_index)

            db.session.commit()
        #end with
    #end function

    def sort(self):
        with app.app_context():
            source_pkg_index = self._generate_source_pkg_index()

            # calculate the sortkeys for packages of same name
            self._sort_source_packages(source_pkg_index)

            db.session.commit()
        #end with
    #end function

    def fix_upstream_refs(self):
        with app.app_context():
            source_pkg_index   = self._generate_source_pkg_index()
            upstream_src_index = self._generate_upstream_src_index()

            self._fix_upstream_refs(source_pkg_index, upstream_src_index)

            db.session.commit()
        #end with
    #end function

    # PRIVATE

    def _generate_source_pkg_index(self):
        source_pkg_index = {}

        query = SourcePackage.query\
                .options(db.defer("xml"))\
                .all()

        for obj in query:
            source_pkg_index \
                    .setdefault(obj.name, {}) \
                    .setdefault(obj.version, obj)
        #end for

        return source_pkg_index
    #end function

    def _generate_upstream_src_index(self):
        upstream_src_index = {}

        for obj in UpstreamSource.query.all():
            upstream_src_index[obj.name] = obj

        return upstream_src_index
    #end function

    def _parse_revisions(self, rules, source_pkg_index, upstream_src_index,
            start_revision=None):
        for revision in rules.revisions(start_rev=start_revision):
            revision.checkout()

            commit_id = revision.commit_id[:8]

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

                xml = etree.tostring(specfile.xml_doc,
                        pretty_print=True, encoding="unicode")

                ref_obj = source_pkg_index \
                        .get(source_name, {})\
                        .get(version)

                if ref_obj is not None:
                    if ref_obj.git_hash != commit_id:
                        self.log.warning(
                            "Package '%s' at '%.8s' in '%s' modified without version bump." %
                                (source_name, revision._commit_id, rules._repo_name)
                        )
                        ref_obj.xml              = xml
                        ref_obj.upstream_version = upstream_version
                        ref_obj.git_hash         = commit_id
                    #end if
                else:
                    ref_obj = SourcePackage(
                        sortkey          = -1,
                        name             = source_name,
                        version          = version,
                        upstream_version = upstream_version,
                        git_hash         = commit_id,
                        xml              = xml,
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

    def _sort_source_packages(self, source_pkg_index):
        for source_name, entries in source_pkg_index.items():
            versions = list(entries.keys())
            versions.sort(key=functools.cmp_to_key(BaseXpkg.compare_versions))

            for i, v in enumerate(versions, start=1):
                entries[v].sortkey = i
        #end for
    #end function

    def _fix_upstream_refs(self, source_pkg_index, upstream_src_index):
        for source_name, entries in source_pkg_index.items():
            upstream_ref_obj = upstream_src_index.get(source_name)

            if upstream_ref_obj is None:
                continue

            for version, ref_obj in entries.items():
                if ref_obj.upstream_version:
                    ref_obj.upstream_source_id = upstream_ref_obj.id_
            #end for
        #end for
    #end function

    def _determine_recentness(self, source_pkg_index, upstream_src_index):
        for source_name, entries in source_pkg_index.items():
            upstream_ref_obj = upstream_src_index.get(source_name)

            if upstream_ref_obj is None:
                continue

            for _, ref_obj in entries.items():
                if not ref_obj.upstream_version:
                    continue

                comp_result = BaseXpkg.compare_versions(
                    ref_obj.upstream_version,
                    upstream_ref_obj.version
                )

                if comp_result < 0:
                    ref_obj.status = SourcePackage.STATUS_BEHIND
                elif comp_result > 0:
                    ref_obj.status = SourcePackage.STATUS_AHEAD
                else:
                    ref_obj.status = SourcePackage.STATUS_CURRENT
            #end for
        #end for
    #end function

#end class

