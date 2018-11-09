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
import sys
import logging
import threading
import traceback

class RepoTask(threading.Thread):

    def __init__(self, name):
        super().__init__()
        self._name      = name
        self._stop_flag = threading.Event()
        self._active    = threading.Event()
        self._lock      = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self.log        = logging.getLogger("org.boltlinux.repository")
    #end function

    def run(self):
        while not self.is_stopped():
            with self._condition:
                if not self._condition.wait_for(self._active.is_set, 0.250):
                    continue
            #end with

            try:
                self.run_task()
            except Exception as e:
                _, exc_value, exc_tb = sys.exc_info()
                frame = traceback.TracebackException(type(exc_value),
                            exc_value, exc_tb, limit=None).stack[-1]
                filename = os.path.basename(frame.filename)
                msg = "Repo task '{}' **CRASH** in '{}' line '{}': {} {}"\
                            .format(self._name, filename, frame.lineno,
                                    type(e).__name__, e)
                self.log.error(msg)
            #end try

            with self._condition:
                self._active.clear()
                self._condition.notify_all()
            #end with
        #end while
    #end function

    def activate(self):
        with self._condition:
            self._active.set()
            self._condition.notify_all()
        #end with
    #end function

    def stop(self):
        with self._lock:
            self._stop_flag.set()

    def is_stopped(self):
        with self._lock:
            return self._stop_flag.is_set()

    def wait_until_done(self, timeout=None):
        def active_is_set():
            return not self._active.is_set()

        with self._condition:
            return self._condition.wait_for(active_is_set, timeout)
    #end function

#end class

