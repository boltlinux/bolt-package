# -*- encoding: utf-8 -*-
#
# Copyright 2005 Brian Beck
#
# The software [in this file] is licensed according to the terms of the PSF
# (Python Software Foundation) license found here:
#
# http://www.python.org/psf/license/
#

class switch(object):
    """
    Taken from http://code.activestate.com/recipes/410692/
    """

    def __init__(self, value):
        self.value = value
        self.fall = False
    #end function

    def __iter__(self):
        """Return the match method once, then stop"""
        yield self.match
        raise StopIteration
    #end function

    def match(self, *args):
        """Indicate whether or not to enter a case suite"""
        if self.fall or not args:
            return True
        elif self.value in args:  # changed for v1.5, see below
            self.fall = True
            return True
        else:
            return False
    #end function

#end class
