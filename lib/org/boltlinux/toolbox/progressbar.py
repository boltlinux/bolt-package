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

import sys

class ProgressBar:

    def __init__(self, total_size, out_file=sys.stdout):
        self._out_file = out_file
        self._total    = total_size
        self._isatty   = self._out_file.isatty()
        self._lastval  = -1
        self._total_reached = False
    #end function

    def __call__(self, amount, total_bars=60):
        if self._total_reached:
            return

        percent = 100 if self._total == 0 else \
                    int(amount * 100.0 / self._total)

        if percent == self._lastval:
            return

        num_bars   = int(percent * total_bars / 100.0)
        num_spaces = total_bars - num_bars

        if self._isatty:
            if amount < self._total:
                self._out_file.write("[" + "#" * num_bars +
                        " " * num_spaces + "] %i%%\r" % percent)
            else:
                self._out_file.write("[" + "#" * num_bars +
                        " " * num_spaces + "] %i%%\n" % percent)
        #end if

        self._lastval = percent

        if amount >= self._total:
            self._total_reached = True
    #end function

#end class
