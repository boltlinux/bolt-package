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
from org.boltlinux.repository.models import SourcePackage
from org.boltlinux.error import MalformedSpecfile

class PackageRules:

    def __init__(self, config):
        self.repositories = config.get("repositories", [])

        self.cache_dir = config.get("cache-dir",
            os.path.realpath(
                os.path.join(
                    AppConfig.get_config_folder(),
                    "cache", "pkg-rules"
                )
            )
        )

        self.log = logging.getLogger("org.boltlinux.repository")
    #end function

    def refresh_package_rules(self):
        for repo_info in self.repositories:
            repo_name  = repo_info["name"]
            repo_url   = repo_info["repo-url"]
            repo_rules = repo_info["rules"]

            checkout_dir = self.cache_dir + os.sep + repo_name

            try:
                if not os.path.exists(checkout_dir):
                    self.__clone_git_repo(repo_rules, checkout_dir)
            except (subprocess.TimeoutExpired,
                    subprocess.CalledProcessError) as e:
                self.log.error("Failed to clone repo %s: %s" %
                        (repo_name, str(e)))
            #end try

            try:
                self.__update_git_checkout(checkout_dir)
            except (subprocess.TimeoutExpired,
                    subprocess.CalledProcessError) as e:
                self.log.error("Failed to update repo %s: %s" %
                        (repo_name, str(e)))
            #end try
        #end for
    #end function

    def update_repository_db(self):
        source_pkg_index = {}

        with app.app_context():
            for obj in SourcePackage.query.all():
                source_pkg_index \
                        .setdefault(obj.name, {}) \
                        .setdefault(obj.version, obj)
            #end for

            for repo_info in self.repositories:
                repo_name  = repo_info["name"]
                repo_url   = repo_info["repo-url"]
                repo_rules = repo_info["rules"]

                checkout_dir = self.cache_dir + os.sep + repo_name

                for specfile in self.__next_specfile(checkout_dir):
                    source_name = specfile.source_name()
                    version     = specfile.latest_version()
                    packages    = specfile.binary_packages()

                    xml = etree.tostring(specfile.xml_doc,
                            pretty_print=True, encoding="unicode")

                    ref_obj = source_pkg_index \
                            .get(source_name, {})\
                            .get(version)

                    if ref_obj is None:
                        source_pkg = SourcePackage(
                            name    = source_name,
                            version = version,
                            xml     = xml
                        )
                        db.session.add(source_pkg)

                        source_pkg_index \
                                .setdefault(source_name, {})\
                                .setdefault(version, source_pkg)
                    #end if
                #end for
            #end for

            db.session.commit()
        #end with
    #end function

    # PRIVATE

    def __next_specfile(self, rules_dir):
        for path, dirs, files in os.walk(rules_dir):
            if "package.xml" in files:
                try:
                    yield Specfile(os.path.join(path, "package.xml"))
                except MalformedSpecfile as e:
                    self.log.error("malformed specfile: %s" % str(e))
                #end try
            #end if
        #end for
    #end function

    def __clone_git_repo(self, url, checkout_dir):
        encoding = sys.getdefaultencoding()

        self.log.info("Cloning %s ..." % url)

        cmd  = ["git", "clone", url, checkout_dir]
        proc = subprocess.run(cmd, timeout=300, check=True,
                stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    #end function

    def __update_git_checkout(self, checkout_dir, branch="master"):
        encoding = sys.getdefaultencoding()

        self.log.info("Running 'git fetch origin' in %s ..." % checkout_dir)
        cmd = ["git", "-C", checkout_dir, "fetch", "origin"]
        subprocess.run(cmd, check=True, stderr=subprocess.PIPE,
                stdout=subprocess.PIPE)

        self.log.info("Running 'git reset --hard origin/%s' in %s ..." %
                (branch, checkout_dir))
        cmd = ["git", "-C", checkout_dir, "reset", "--hard", "origin/" + branch]
        subprocess.run(cmd, check=True, stderr=subprocess.PIPE,
                stdout=subprocess.PIPE)
    #end function

#end class

