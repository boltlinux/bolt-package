#!/usr/bin/env python3
#-*- encoding: utf-8 -*-

import tempfile
import os, sys, unittest

SOURCES_DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.realpath(sys.argv[0])),
    "..", ".."
))

sys.path.insert(1, SOURCES_DIR + os.sep + 'lib')

from org.boltlinux.repository.debiansourceslist import DebianSourcesList

class UTTestRepositorySourcesList(unittest.TestCase):

    def test_download_and_iter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sources_list = DebianSourcesList(cache_dir=tmpdir)

            sources = list(sources_list)
            self.assertTrue(len(sources) == 0)

            self.assertFalse(sources_list.is_up2date())
            sources_list.refresh()
            self.assertTrue(sources_list.is_up2date())

            sources = list(sources_list)
            self.assertTrue(len(sources) > 0)

            pkg_info = sources[0]

            for key in ["Package", "Version"]:
                self.assertTrue(key in pkg_info)
        #end with
    #end function

#end class

