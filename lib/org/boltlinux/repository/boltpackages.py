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

from org.boltlinux.package.appconfig import AppConfig
from org.boltlinux.repository.flaskinit import app, db
from org.boltlinux.repository.models import SourcePackage, BinaryPackage
from org.boltlinux.repository.boltpackageslist import BoltPackagesList
from org.boltlinux.repository.repotask import RepoTask
from org.boltlinux.error import RepositoryError
from org.boltlinux.package.xpkg import BaseXpkg

class BoltPackages(RepoTask):

    def __init__(self, config, verbose=True):
        super().__init__("bolt-packages")

        release = config.get("release", {})

        self._verbose       = verbose
        self._repositories  = config.get("repositories", [])
        self._release       = release.get("id", "stable")
        self._architectures = release.get("supported-architectures", {})

        self._cache_dir  = \
            config.get("cache-dir",
                os.path.realpath(
                    os.path.join(
                        AppConfig.get_config_folder(),
                        "cache", "lists", self._release
                    )
                )
            )

        self.log = logging.getLogger("org.boltlinux.repository")
    #end function

    def run_task(self):
        self.refresh()
        self.update_db()
    #end function

    def refresh(self):
        for repo_info in self._repositories:
            for libc, archlist in self._architectures.items():
                for arch in archlist:
                    if self.is_stopped():
                        return

                    repo_name = repo_info["name"]
                    repo_url  = repo_info["repo-url"]

                    packages_list = BoltPackagesList(
                        release   = self._release,
                        component = "main",
                        arch      = arch,
                        mirror    = repo_url,
                        cache_dir = self._cache_dir
                    )

                    try:
                        if not packages_list.is_up2date():
                            if self._verbose:
                                self.log.info(
                                    "Refreshing packages list for "
                                        "'%s', libc '%s', arch '%s'." %
                                                (repo_name, libc, arch))
                            #end if

                            packages_list.refresh()
                    except RepositoryError as e:
                        msg = "Failed to refresh Bolt packages list for "\
                                "repo '%s', libc '%s', arch '%s': %s"
                        self.log.error(msg % (repo_name, libc, arch, str(e)))
                    #end try
                #end for
            #end for
        #end for
    #end function

    def update_db(self):
        with app.app_context():
            source_pkg_index = self._generate_source_pkg_index()
            binary_pkg_index = self._generate_binary_pkg_index()

            for repo_info in self._repositories:
                repo_name = repo_info["name"]
                repo_url  = repo_info["repo-url"]

                for libc, archlist in self._architectures.items():
                    for arch in archlist:
                        if self.is_stopped():
                            return

                        if self._verbose:
                            self.log.info(
                                "Updating package DB entries for '%s', "
                                    "libc '%s', arch '%s'." %
                                        (repo_name, libc, arch))
                        #end if

                        packages_list = BoltPackagesList(
                            release   = self._release,
                            component = "main",
                            libc      = libc,
                            arch      = arch,
                            mirror    = repo_url,
                            cache_dir = self._cache_dir
                        )

                        binary_pkg_subindex = binary_pkg_index\
                                .setdefault(libc, {})\
                                .setdefault(arch, {})

                        self._parse_revisions(packages_list, source_pkg_index,
                                binary_pkg_subindex, repo_name)
                    #end for
                #end for
            #end for

            # calculate the sortkeys for packages of same name
            self._sort_packages(binary_pkg_index)

            db.session.commit()
        #end with
    #end function

    # PRIVATE

    def _generate_source_pkg_index(self):
        source_pkg_index = {}

        query = SourcePackage.query\
                .options(db.defer("json"))\
                .all()

        for obj in query:
            source_pkg_index \
                    .setdefault(obj.name, {}) \
                    .setdefault(obj.version, obj)
        #end for

        return source_pkg_index
    #end function

    def _generate_binary_pkg_index(self):
        binary_pkg_index = {}

        for obj in BinaryPackage.query.all():
            binary_pkg_index \
                    .setdefault(obj.libc, {}) \
                    .setdefault(obj.arch, {}) \
                    .setdefault(obj.name, {}) \
                    .setdefault(obj.version, obj)

        return binary_pkg_index
    #end function

    def _parse_revisions(self, packages_list, source_pkg_index,
            binary_pkg_index, repo_name):
        for pkg_info in packages_list:
            if self.is_stopped():
                break

            pkg_name     = pkg_info["Package"]
            pkg_version  = pkg_info["Version"]
            pkg_source   = pkg_info["Source"]
            arch_indep   = pkg_info["Architecture"] == "all"
            pkg_filename = pkg_info["Filename"]

            if pkg_source is not None:
                source_ref_obj = source_pkg_index \
                    .get(pkg_source, {}) \
                    .get(pkg_version)

                if source_ref_obj is None:
                    self.log.error(
                        "Source '%s' not found for package '%s' on for %s on %s" %
                            (pkg_source, pkg_name, packages_list.libc,
                                packages_list.arch))
                    continue
                #end if
            #end if

            if not binary_pkg_index.get(pkg_name, {}).get(pkg_version):
                binary_pkg = BinaryPackage(
                    source_package_id = source_ref_obj.id_,
                    libc       = packages_list.libc,
                    arch       = packages_list.arch,
                    name       = pkg_name,
                    version    = pkg_version,
                    component  = packages_list.component,
                    repo_name  = repo_name,
                    filename   = pkg_filename,
                    arch_indep = arch_indep
                )
                db.session.add(binary_pkg)

                binary_pkg_index.setdefault(pkg_name, {})[pkg_version] = \
                        binary_pkg
            #end if
        #end for
    #end function

    def _sort_packages(self, binary_pkg_index):
        for libc, arch_list in binary_pkg_index.items():
            for arch in arch_list:
                for pkg_name, entries in binary_pkg_index[libc][arch].items():
                    if self.is_stopped():
                        return

                    versions = list(entries.keys())
                    versions.sort(key=functools.cmp_to_key(BaseXpkg.compare_versions))

                    for i, v in enumerate(versions, start=1):
                        entries[v].sortkey = i
                #end for
            #end for
        #end for
    #end function

#end class

