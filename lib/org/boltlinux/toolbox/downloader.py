# -*- encoding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2019 Tobias Koch <tobias.koch@gmail.com>
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

import urllib.request

from org.boltlinux.error import BoltError

class DownloadError(BoltError):
    pass

class Downloader:

    def __init__(self, progress_bar_class=None):
        self._progress_bar_class = progress_bar_class

    def get(self, url):
        progress_bar = None
        bytes_read   = 0

        try:
            with urllib.request.urlopen(url) as response:
                if self._progress_bar_class and response.length:
                    progress_bar = self._progress_bar_class(response.length)
                    progress_bar(0)
                #end if

                for chunk in iter(lambda: response.read(8192), b""):
                    bytes_read += len(chunk)

                    yield chunk

                    if progress_bar:
                        progress_bar(bytes_read)
                #end for
            #end with
        except urllib.error.URLError as e:
            raise DownloadError("error retrieving '%s': %s" % (url, str(e)))
    #end function

#end class
