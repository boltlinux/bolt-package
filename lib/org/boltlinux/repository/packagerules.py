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

        git_fetch_origin = ["git", "-C", self.rules_dir, "fetch", "origin"]
        git_reset_hard   = ["git", "-C", self.rules_dir, "reset", "--hard",
                "origin/" + self._branch]

        for command in [git_fetch_origin, git_reset_hard]:
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

        stdout = sys.stdout if verbose else subprocess.PIPE
        stderr = sys.stderr if verbose else subprocess.PIPE

        if start_rev is not None:
            git_rev_list += [start_rev + ".." + self._branch]
        else:
            git_rev_list += [self._branch]

        try:
            git_rev_list_result = subprocess.run(git_rev_list, timeout=300,
                    check=True, stdout=subprocess.PIPE, stderr=stderr)
        except subprocess.CalledProcessError as e:
            raise RepositoryError("error fetching rev-list: %s" % str(e))

        preferred_encoding = locale.getpreferredencoding()

        revision_list = git_rev_list_result\
                .stdout\
                .decode(preferred_encoding)\
                .splitlines()

        for commit_id in revision_list:
            if not commit_id.strip():
                continue
            yield Revision(commit_id, self.rules_dir, self._branch)
        #end for
    #end function

    @property
    def rules_dir(self):
        return os.path.join(self._cache_dir, self._repo_name)

#end class

class Revision:

    def __init__(self, commit_id, rules_dir, branch):
        self._commit_id = commit_id
        self._rules_dir = rules_dir
        self._branch    = branch
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

    def rules(self):
        for path, dirs, files in os.walk(self._rules_dir):
            if "package.xml" in files:
                yield os.path.join(path, "package.xml")
        #end for
    #end function

#end class

