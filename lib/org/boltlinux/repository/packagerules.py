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
import locale

from org.boltlinux.error import RepositoryError

class PackageRules:

    def __init__(self, name, rules_url, cache_dir=None):
        self._repo_name = name

        if "@" in rules_url:
            self._rules_url, self._branch = rules_url.rsplit("@", 1)
        else:
            self._rules_url, self._branch = rules_url, "master"

        self._cache_dir = cache_dir or os.path.realpath(
            os.path.join(
                AppConfig.get_config_folder(),
                "cache", "upstream"
            )
        )
    #end function

    def clone(self, verbose=False):
        if os.path.exists(os.path.join(self.rules_dir, ".git")):
            return

        stdout = sys.stdout if verbose else subprocess.PIPE
        stderr = sys.stderr if verbose else subprocess.PIPE

        git_clone = ["git", "clone", self._rules_url, self.rules_dir]

        try:
            proc = subprocess.run(git_clone, timeout=300, check=True,
                    stdout=stdout, stderr=stderr)
        except subprocess.CalledProcessError as e:
            raise RepositoryError("failed to clone '%s': %s" %
                    (self._rules_url, str(e)))
        #end try
    #end function

    def refresh(self, verbose=False):
        if not os.path.exists(os.path.join(self.rules_dir, ".git")):
            self.clone(verbose=verbose)

        stdout = sys.stdout if verbose else subprocess.PIPE
        stderr = sys.stderr if verbose else subprocess.PIPE

        git_base_cmd = ["git", "-C", self.rules_dir]

        git_fetch_origin = git_base_cmd + ["fetch",    "origin"    ]
        git_checkout     = git_base_cmd + ["checkout", self._branch]
        git_reset_hard   = git_base_cmd + ["reset", "--hard", "origin/" + self._branch]
        git_clean_xfd    = git_base_cmd + ["clean",    "-xfd"      ]

        git_commands_to_run = [
            git_fetch_origin,
            git_checkout,
            git_reset_hard,
            git_clean_xfd
        ]

        for command in git_commands_to_run:
            try:
                proc = subprocess.run(command, timeout=300, check=True,
                        stdout=stdout, stderr=stderr)
            except subprocess.CalledProcessError as e:
                raise RepositoryError("failed to refresh '%s': %s" %
                        (self.rules_dir, str(e)))
            #end try
        #end for
    #end function

    def revisions(self, start_rev=None, verbose=False):
        git_rev_list = ["git", "-C", self.rules_dir, "rev-list", "--reverse"]

        stderr = sys.stderr if verbose else subprocess.PIPE

        if start_rev is not None:
            git_rev_list += [start_rev + ".." + self._branch]
        else:
            if self._branch == "master":
                git_rev_list += [self._branch]
            else:
                # history since we branched off of master
                git_rev_list += ["master" + ".." + self._branch]
            #end if
        #end if

        try:
            git_rev_list_result = subprocess.run(git_rev_list, timeout=300,
                    check=True, stdout=subprocess.PIPE, stderr=stderr)
        except subprocess.CalledProcessError as e:
            raise RepositoryError("error fetching rev-list: %s" % str(e))

        preferred_encoding = locale.getpreferredencoding()

        revision_list = git_rev_list_result\
                .stdout\
                .decode(preferred_encoding)\
                .strip()\
                .splitlines()

        prev_revision = start_rev

        if prev_revision is None and len(revision_list) == 0:
            revision_list.insert(0, self.get_head_hash(verbose=verbose))

        for commit_id in revision_list:
            if not commit_id.strip():
                continue
            yield Revision(commit_id, self.rules_dir, self._branch,
                    prev_revision=prev_revision)
            prev_revision = commit_id
        #end for
    #end function

    @property
    def rules_dir(self):
        return os.path.join(self._cache_dir, self._repo_name)

    def get_head_hash(self, verbose=False):
        git_rev_parse = ["git", "-C", self.rules_dir, "rev-parse", self._branch]

        stderr = sys.stderr if verbose else subprocess.PIPE

        try:
            git_rev_parse_result = subprocess.run(git_rev_parse, timeout=300,
                    check=True, stdout=subprocess.PIPE, stderr=stderr)
        except subprocess.CalledProcessError as e:
            raise RepositoryError("error retrieving hash for HEAD: %s" % str(e))

        preferred_encoding = locale.getpreferredencoding()

        revision = git_rev_parse_result\
                .stdout\
                .decode(preferred_encoding)\
                .strip()

        return revision
    #end function

#end class

class Revision:

    def __init__(self, commit_id, rules_dir, branch, prev_revision=None):
        self._commit_id = commit_id
        self._rules_dir = rules_dir
        self._branch    = branch
        self._prev_rev  = prev_revision
    #end function

    def checkout(self, verbose=False):
        git_checkout = ["git", "-C", self._rules_dir, "checkout",
                self._commit_id]

        stdout = sys.stdout if verbose else subprocess.PIPE
        stderr = sys.stderr if verbose else subprocess.PIPE

        try:
            subprocess.run(git_checkout, timeout=300, check=True,
                    stdout=stdout, stderr=stderr)
        except subprocess.CalledProcessError as e:
            raise RepositoryError("error checking out '%s': %s" %
                    (self._commit_id, str(e)))
        #end try
    #end function

    def rules(self, verbose=False):
        stderr = sys.stderr if verbose else subprocess.PIPE

        if self._prev_rev is None:
            for path, dirs, files in os.walk(self._rules_dir):
                if "package.xml" in files:
                    yield os.path.join(path, "package.xml")
            #end for
        else:
            git_diff_tree = [
                "git", "-C", self._rules_dir,
                "diff-tree", "--no-commit-id", "--name-only",  "-r",
                self._prev_rev + ".." + self._commit_id
            ]

            try:
                git_diff_tree_result = subprocess.run(git_diff_tree,
                        timeout=300, check=True, stdout=subprocess.PIPE,
                        stderr=stderr)
            except subprocess.CalledProcessError as e:
                raise RepositoryError("error doing a diff-tree in '%s': %s" %
                        (self._commit_id, str(e)))
            #end try

            preferred_encoding = locale.getpreferredencoding()

            changed_files = git_diff_tree_result\
                .stdout\
                .decode(preferred_encoding)\
                .strip()\
                .splitlines()

            directory_list = list(
                set([os.path.dirname(p) for p in changed_files])
            )

            for directory in directory_list:
                package_xml = os.path.join(self._rules_dir, directory,
                        "package.xml")
                if os.path.exists(package_xml):
                    yield package_xml
            #end for
        #end if
    #end function

    @property
    def commit_id(self):
        return self._commit_id

#end class

