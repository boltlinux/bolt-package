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

import threading

from org.boltlinux.repository.debiansources import DebianSources
from org.boltlinux.repository.boltsources import BoltSources
from org.boltlinux.repository.boltpackages import BoltPackages
from org.boltlinux.repository.boltpackagescan import BoltPackageScan

class RepoUpdater:

    def __init__(self, config):
        self._stop_flag = threading.Event()
        self._activate  = threading.Event()
        self._condition = threading.Condition()

        self._tasks  = [
            DebianSources(config),
            BoltSources(config),
            BoltPackages(config),
            BoltPackageScan(config)
        ]
    #end function

    def run(self):
        for t in self._tasks:
            t.start()

        while not self._stop_flag.is_set():
            for t in self._tasks:
                t.activate()
                while not self._stop_flag.is_set():
                    if t.wait_until_done(0.250):
                        break
            #end for

            with self._condition:
                while not self._stop_flag.is_set():
                    if self._condition.wait_for(self._activate.is_set, 0.250):
                        break
                self._activate.clear()
            #end with
        #end while

        for t in self._tasks:
            t.stop()
        for t in self._tasks:
            t.join()
    #end function

    def activate(self, *args):
        with self._condition:
            self._activate.set()

    def stop(self, *args):
        self._stop_flag.set()

#end class
