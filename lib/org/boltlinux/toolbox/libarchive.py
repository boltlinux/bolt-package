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
import re
import ctypes
import stat
import pwd
import grp

from ctypes.util import find_library

lib = ctypes.cdll.LoadLibrary(find_library("archive"))

################################## CONSTANTS ##################################

FORMAT_AR = 1
FORMAT_AR_BSD = 2
FORMAT_AR_SVR4 = 3
FORMAT_CPIO = 4
FORMAT_CPIO_NEWC = 5
FORMAT_MTREE = 6
FORMAT_TAR = 7
FORMAT_TAR_GNUTAR = 8
FORMAT_TAR_PAX_INTERCHANGE = 9
FORMAT_TAR_PAX_RESTRICTED = 10
FORMAT_TAR_USTAR = 11
FORMAT_TAR_OLDTAR = 12
FORMAT_ZIP = 13
FORMAT_RAW = 14

COMPRESSION_BZIP2 = 14
COMPRESSION_COMPRESS = 15
COMPRESSION_GZIP = 16
COMPRESSION_LZMA = 17
COMPRESSION_XZ = 18
COMPRESSION_NONE = 19

STATUS_OK = 0
STATUS_EOF = 1

################################### CTYPES ####################################

_format_functions = {
    FORMAT_AR: "archive_write_set_format_ar_svr4",
    FORMAT_AR_BSD: "archive_write_set_format_ar_bsd",
    FORMAT_AR_SVR4: "archive_write_set_format_ar_svr4",
    FORMAT_CPIO: "archive_write_set_format_cpio",
    FORMAT_CPIO_NEWC: "archive_write_set_format_cpio_newc",
    FORMAT_MTREE: "archive_write_set_format_mtree",
    FORMAT_TAR: "archive_write_set_format_ustar",
    FORMAT_TAR_GNUTAR: "archive_write_set_format_gnutar",
    FORMAT_TAR_PAX_INTERCHANGE: "archive_write_set_format_pax",
    FORMAT_TAR_PAX_RESTRICTED: "archive_write_set_format_pax_restricted",
    FORMAT_TAR_USTAR: "archive_write_set_format_ustar",
    FORMAT_ZIP: "archive_write_set_format_zip",
    FORMAT_RAW: "archive_write_set_format_raw",
}

for func_name in _format_functions.values():
    try:
        func = getattr(lib, func_name)
        func.argtypes = [ctypes.c_void_p]
    except AttributeError:
        pass
#end for

_compression_functions = {
    COMPRESSION_BZIP2: "archive_write_add_filter_bzip2",
    COMPRESSION_COMPRESS: "archive_write_add_filter_compress",
    COMPRESSION_GZIP: "archive_write_add_filter_gzip",
    COMPRESSION_LZMA: "archive_write_add_filter_lzma",
    COMPRESSION_XZ: "archive_write_add_filter_xz",
    COMPRESSION_NONE: "archive_write_add_filter_none",
    None: "archive_write_add_filter_none"
}

for func_name in _compression_functions.values():
    try:
        func = getattr(lib, func_name)
        func.argtypes = [ctypes.c_void_p]
    except AttributeError:
        pass
#end for

lib.archive_entry_atime.argtypes = [ctypes.c_void_p]
lib.archive_entry_atime.restype = ctypes.c_int
lib.archive_entry_clear.argtypes = [ctypes.c_void_p]
lib.archive_entry_clear.restype = ctypes.c_void_p
lib.archive_entry_clone.argtypes = [ctypes.c_void_p]
lib.archive_entry_clone.restype = ctypes.c_void_p
lib.archive_entry_copy_gname.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lib.archive_entry_copy_gname.restype = None
lib.archive_entry_copy_hardlink.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lib.archive_entry_copy_hardlink.restype = None
lib.archive_entry_copy_pathname.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lib.archive_entry_copy_pathname.restype = None
lib.archive_entry_copy_symlink.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lib.archive_entry_copy_symlink.restype = None
lib.archive_entry_copy_uname.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lib.archive_entry_copy_uname.restype = None
lib.archive_entry_ctime.argtypes = [ctypes.c_void_p]
lib.archive_entry_ctime.restype = ctypes.c_int
lib.archive_entry_dev.argtypes = [ctypes.c_void_p]
lib.archive_entry_dev.restype = ctypes.c_ulong
lib.archive_entry_devmajor.argtypes = [ctypes.c_void_p]
lib.archive_entry_devmajor.restype = ctypes.c_uint
lib.archive_entry_devminor.argtypes = [ctypes.c_void_p]
lib.archive_entry_devminor.restype = ctypes.c_uint
lib.archive_entry_filetype.argtypes = [ctypes.c_void_p]
lib.archive_entry_filetype.restype = ctypes.c_uint
lib.archive_entry_free.argtypes = [ctypes.c_void_p]
lib.archive_entry_free.restype = None
lib.archive_entry_gid.argtypes = [ctypes.c_void_p]
lib.archive_entry_gid.restype = ctypes.c_ulong
lib.archive_entry_gname.argtypes = [ctypes.c_void_p]
lib.archive_entry_gname.restype = ctypes.c_char_p
lib.archive_entry_hardlink.argtypes = [ctypes.c_void_p]
lib.archive_entry_hardlink.restype = ctypes.c_char_p
lib.archive_entry_ino.argtypes = [ctypes.c_void_p]
lib.archive_entry_ino.restype = ctypes.c_ulong
lib.archive_entry_mode.argtypes = [ctypes.c_void_p]
lib.archive_entry_mode.restype = ctypes.c_int
lib.archive_entry_mtime.argtypes = [ctypes.c_void_p]
lib.archive_entry_mtime.restype = ctypes.c_int
lib.archive_entry_new.argtypes = []
lib.archive_entry_new.restype = ctypes.c_void_p
lib.archive_entry_nlink.argtypes = [ctypes.c_void_p]
lib.archive_entry_nlink.restype = ctypes.c_uint
lib.archive_entry_pathname.argtypes = [ctypes.c_void_p]
lib.archive_entry_pathname.restype = ctypes.c_char_p
lib.archive_entry_rdevmajor.argtypes = [ctypes.c_void_p]
lib.archive_entry_rdevmajor.restype = ctypes.c_uint
lib.archive_entry_rdevminor.argtypes = [ctypes.c_void_p]
lib.archive_entry_rdevminor.restype = ctypes.c_uint
lib.archive_entry_set_atime.argtypes = \
    [ctypes.c_void_p, ctypes.c_int, ctypes.c_ulong]
lib.archive_entry_set_atime.restype = None
lib.archive_entry_set_ctime.argtypes = \
    [ctypes.c_void_p, ctypes.c_int, ctypes.c_ulong]
lib.archive_entry_set_ctime.restype = None
lib.archive_entry_set_dev.argtypes = [ctypes.c_void_p, ctypes.c_long]
lib.archive_entry_set_dev.restype = None
lib.archive_entry_set_devmajor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
lib.archive_entry_set_devmajor.restype = None
lib.archive_entry_set_devminor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
lib.archive_entry_set_devminor.restype = None
lib.archive_entry_set_filetype.argtypes = [ctypes.c_void_p, ctypes.c_uint]
lib.archive_entry_set_filetype.restype = None
lib.archive_entry_set_gid.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
lib.archive_entry_set_gid.restype = None
lib.archive_entry_set_ino.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
lib.archive_entry_set_ino.restype = None
lib.archive_entry_set_mode.argtypes = [ctypes.c_void_p, ctypes.c_int]
lib.archive_entry_set_mode.restype = None
lib.archive_entry_set_mtime.argtypes = \
    [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]
lib.archive_entry_set_mtime.restype = None
lib.archive_entry_set_nlink.argtypes = [ctypes.c_void_p, ctypes.c_uint]
lib.archive_entry_set_nlink.restype = None
lib.archive_entry_set_rdevmajor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
lib.archive_entry_set_rdevmajor.restype = None
lib.archive_entry_set_rdevminor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
lib.archive_entry_set_rdevminor.restype = None
lib.archive_entry_set_size.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
lib.archive_entry_set_size.restype = None
lib.archive_entry_set_uid.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
lib.archive_entry_set_uid.restype = None
lib.archive_entry_size.argtypes = [ctypes.c_void_p]
lib.archive_entry_size.restype = ctypes.c_ulong
lib.archive_entry_symlink.argtypes = [ctypes.c_void_p]
lib.archive_entry_symlink.restype = ctypes.c_char_p
lib.archive_entry_uid.argtypes = [ctypes.c_void_p]
lib.archive_entry_uid.restype = ctypes.c_ulong
lib.archive_entry_uname.argtypes = [ctypes.c_void_p]
lib.archive_entry_uname.restype = ctypes.c_char_p

lib.archive_error_string.argtypes = [ctypes.c_void_p]
lib.archive_error_string.restype = ctypes.c_char_p

lib.archive_write_free.argtypes = [ctypes.c_void_p]
lib.archive_write_free.restype = ctypes.c_int
lib.archive_write_header.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
lib.archive_write_header.restype = ctypes.c_int
lib.archive_write_new.argtypes = []
lib.archive_write_new.restype = ctypes.c_void_p
lib.archive_write_open_filename.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lib.archive_write_open_filename.restype = ctypes.c_int
lib.archive_write_data.argtypes = \
    [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
lib.archive_write_data.restype = ctypes.c_ssize_t

lib.archive_read_free.argtypes = [ctypes.c_void_p]
lib.archive_write_free.restype = ctypes.c_int
lib.archive_read_data.argtypes = \
    [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
lib.archive_read_data.restype = ctypes.c_ssize_t
lib.archive_read_new.argtypes = []
lib.archive_read_new.restype = ctypes.c_void_p
lib.archive_read_next_header2.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
lib.archive_read_next_header2.restype = ctypes.c_int
lib.archive_read_open_filename.argtypes = \
    [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_ulong]
lib.archive_read_open_filename.restype = ctypes.c_int
lib.archive_read_support_filter_all.argtypes = [ctypes.c_void_p]
lib.archive_read_support_filter_all.restype = ctypes.c_int
lib.archive_read_support_filter_program.argtypes = \
    [ctypes.c_void_p, ctypes.c_char_p]
lib.archive_read_support_filter_program.restype = ctypes.c_int
lib.archive_read_support_format_all.argtypes = [ctypes.c_void_p]
lib.archive_read_support_format_all.restype = ctypes.c_int
lib.archive_read_support_format_raw.argtypes = [ctypes.c_void_p]
lib.archive_read_support_format_raw.restype = ctypes.c_int
lib.archive_read_support_format_empty.argtypes = [ctypes.c_void_p]
lib.archive_read_support_format_empty.restype = ctypes.c_int

lib.archive_write_set_option.argtypes = \
    [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
lib.archive_write_set_option.restype = ctypes.c_int

############################### IMPLEMENTATION ################################

def error_string(c_archive_p):
    return lib.archive_error_string(c_archive_p).decode("utf-8")

class ArchiveError(Exception):
    pass

class ArchiveEntry:

    def __init__(self):
        self._c_entry_p = lib.archive_entry_new()

    def __del__(self):
        self.free()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.free()

    def free(self):
        if self._c_entry_p:
            lib.archive_entry_free(self._c_entry_p)
            self._c_entry_p = None
    #end function

    def clear(self):
        lib.archive_entry_clear(self._c_entry_p)

    @property
    def is_file(self):
        return stat.S_ISREG(self.filetype) != 0 and not self.is_hardlink

    @property
    def is_directory(self):
        return stat.S_ISDIR(self.filetype) != 0

    @property
    def is_symbolic_link(self):
        return stat.S_ISLNK(self.filetype) != 0

    @property
    def is_block_device(self):
        return stat.S_ISBLK(self.filetype) != 0

    @property
    def is_char_device(self):
        return stat.S_ISCHR(self.filetype) != 0

    @property
    def is_fifo(self):
        return stat.S_ISFIFO(self.filetype) != 0

    @property
    def is_socket(self):
        return stat.S_ISSOCK(self.filetype) != 0

    @property
    def is_hardlink(self):
        return bool(lib.archive_entry_hardlink(self._c_entry_p))

    @property
    def filetype(self):
        return lib.archive_entry_filetype(self._c_entry_p) & 0o170000

    @filetype.setter
    def filetype(self, filetype):
        lib.archive_entry_set_filetype(self._c_entry_p, filetype)

    @property
    def devmajor(self):
        return lib.archive_entry_devmajor(self._c_entry_p)

    @devmajor.setter
    def devmajor(self, devmajor):
        lib.archive_entry_set_devmajor(self._c_entry_p, devmajor)

    @property
    def devminor(self):
        return lib.archive_entry_devminor(self._c_entry_p)

    @devminor.setter
    def devminor(self, devminor):
        lib.archive_entry_set_devminor(self._c_entry_p, devminor)

    @property
    def atime(self):
        return lib.archive_entry_atime(self._c_entry_p)

    @atime.setter
    def atime(self, atime):
        lib.archive_entry_set_atime(self._c_entry_p, atime, 0)

    @property
    def ctime(self):
        return lib.archive_entry_ctime(self._c_entry_p)

    @ctime.setter
    def ctime(self, ctime):
        lib.archive_entry_set_ctime(self._c_entry_p, ctime, 0)

    def clone(self):
        return ArchiveEntry(lib.archive_entry_clone(self._c__entry_p))

    @property
    def dev(self):
        return lib.archive_entry_dev(self._c_entry_p)

    @dev.setter
    def dev(self, dev):
        lib.archive_entry_set_dev(self._c_entry_p, dev)

    @property
    def gid(self):
        return lib.archive_entry_gid(self._c_entry_p)

    @gid.setter
    def gid(self, gid):
        lib.archive_entry_set_gid(self._c_entry_p, gid)

    @property
    def gname(self):
        return lib.archive_entry_gname(self._c_entry_p).decode("utf-8")

    @gname.setter
    def gname(self, gname):
        lib.archive_entry_copy_gname(self._c_entry_p, gname.encode("utf-8"))

    @property
    def hardlink(self):
        return lib.archive_entry_hardlink(self._c_entry_p).decode("utf-8")

    @hardlink.setter
    def hardlink(self, hardlink):
        lib.archive_entry_copy_hardlink(self._c_entry_p,
                hardlink.encode("utf-8"))

    @property
    def inode(self):
        return lib.archive_entry_ino(self._c_entry_p)

    @inode.setter
    def inode(self, inode):
        lib.archive_entry_set_ino(self._c_entry_p, inode)

    @property
    def mode(self):
        return lib.archive_entry_mode(self._c_entry_p) & 0o7777

    @mode.setter
    def mode(self, mode):
        lib.archive_entry_set_mode(self._c_entry_p, mode)

    @property
    def mtime(self):
        return lib.archive_entry_mtime(self._c_entry_p)

    @mtime.setter
    def mtime(self, mtime):
        lib.archive_entry_set_mtime(self._c_entry_p, mtime, 0)

    @property
    def nlink(self):
        return lib.archive_entry_nlink(self._c_entry_p)

    @nlink.setter
    def nlink(self, nlink):
        lib.archive_entry_set_nlink(self._c_entry_p, nlink)

    @property
    def pathname(self):
        return lib.archive_entry_pathname(self._c_entry_p).decode("utf-8")

    @pathname.setter
    def pathname(self, pathname):
        lib.archive_entry_copy_pathname(self._c_entry_p,
                pathname.encode("utf-8"))
    #end function

    @property
    def rdevmajor(self):
        return lib.archive_entry_rdevmajor(self._c_entry_p)

    @rdevmajor.setter
    def rdevmajor(self, rdevmajor):
        lib.archive_entry_set_rdevmajor(self._c_entry_p, rdevmajor)

    @property
    def rdevminor(self):
        return lib.archive_entry_rdevminor(self._c_entry_p)

    @rdevminor.setter
    def rdevminor(self, rdevminor):
        lib.archive_entry_set_rdevminor(self._c_entry_p, rdevminor)

    @property
    def size(self):
        return lib.archive_entry_size(self._c_entry_p)

    @size.setter
    def size(self, size):
        lib.archive_entry_set_size(self._c_entry_p, size)

    @property
    def symlink(self):
        return lib.archive_entry_symlink(self._c_entry_p).decode("utf-8")

    @symlink.setter
    def symlink(self, symlink):
        lib.archive_entry_copy_symlink(self._c_entry_p,
                symlink.encode("utf-8"))
    #end function

    @property
    def uid(self):
        lib.archive_entry_uid(self._c_entry_p)

    @uid.setter
    def uid(self, uid):
        lib.archive_entry_set_uid(self._c_entry_p, uid)

    @property
    def uname(self):
        return lib.archive_entry_uname(self._c_entry_p).decode("utf-8")

    @uname.setter
    def uname(self, uname):
        lib.archive_entry_copy_uname(self._c_entry_p,
                uname.encode("utf-8"))
    #end function

    def copy_stat(self, filename, no_atime=False, no_mtime=False,
            no_ctime=False):
        if not os.path.exists(filename):
            raise ArchiveError("no such file or directory: '%s'" % filename)

        kwargs = {
            "no_atime": no_atime,
            "no_mtime": no_mtime,
            "no_ctime": no_ctime
        }

        self._copy_raw_stat(os.lstat(filename), **kwargs)
    #end function

    def _copy_raw_stat(self, stats, **kwargs):
        no_atime = kwargs.get("no_atime", False)
        no_mtime = kwargs.get("no_mtime", False)
        no_ctime = kwargs.get("no_ctime", False)

        self.filetype = stats.st_mode
        self.mode     = stats.st_mode
        self.dev      = stats.st_dev
        self.inode    = stats.st_ino
        self.nlink    = stats.st_nlink

        self.uid      = stats.st_uid
        self.gid      = stats.st_gid

        try:
            self.uname = pwd.getpwuid(stats.st_uid).pw_name
        except KeyError:
            pass
        try:
            self.gname = grp.getgrgid(stats.st_gid).gr_name
        except KeyError:
            pass

        self.size     = stats.st_size

        if not no_atime:
            self.atime = int(stats.st_atime)
        if not no_mtime:
            self.mtime = int(stats.st_mtime)
        if not no_ctime:
            self.ctime = int(stats.st_ctime)
    #end function

#end class

class ArchiveFileWriter:

    def __init__(self, filename, archive_format, compression=None,
            options=None):
        self._c_archive_p = lib.archive_write_new()
        self._hardlinks = {}

        try:
            func = getattr(lib, _compression_functions[compression])
            func(self._c_archive_p)
        except (KeyError, AttributeError):
            self.close()
            raise ArchiveError("invalid or unsupported compression scheme.")
        #end try

        try:
            func = getattr(lib, _format_functions[archive_format])
            func(self._c_archive_p)
        except (KeyError, AttributeError):
            self.close()
            raise ArchiveError("invalid or unsupported archive format.")
        #end try

        if options is not None:
            for mod, key, val in options:
                self.__set_filter_option(mod, key, val)
        #end if

        if lib.archive_write_open_filename(
                self._c_archive_p, filename.encode("utf-8")) != STATUS_OK:
            msg = error_string(self._c_archive_p)
            self.close()
            raise ArchiveError(msg)
        #end if
    #end function

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        if self._c_archive_p:
            lib.archive_write_free(self._c_archive_p)
            self._c_archive_p = None
    #end function

    def write_entry(self, entry):
        if not isinstance(entry, ArchiveEntry):
            msg = "first argument to write_entry must be an ArchiveEntry."
            raise ValueError(msg)

        # automatic hardlink handling
        if entry.nlink > 1 and entry.inode:
            path = self._hardlinks.setdefault(entry.dev, {}).get(entry.inode)

            if not path:
                self._hardlinks[entry.dev][entry.inode] = entry.pathname
            else:
                entry.hardlink = path
            #end if
        #end if

        if lib.archive_write_header(self._c_archive_p,
                entry._c_entry_p) != STATUS_OK:
            raise ArchiveError(error_string(self._c_archive_p))
    #end function

    def write_data(self, data):
        if not isinstance(data, bytes):
            msg = "data passed to write_data has to be a 'bytes' string."
            raise ValueError(msg)
        bytes_written = lib.archive_write_data(self._c_archive_p,
                data, len(data))
        if bytes_written < 0:
            raise ArchiveError(error_string(self._c_archive_p))
        return bytes_written
    #end function

    def add_file(self, source_file, pathname=None, uname=None, gname=None):
        if not os.path.isfile(source_file):
            raise ArchiveError("No such file: {}".format(source_file))
        if not pathname:
            pathname = source_file

        with ArchiveEntry() as archive_entry:
            archive_entry.copy_stat(source_file)
            archive_entry.pathname = pathname

            if uname:
                archive_entry.uname = uname
            if gname:
                archive_entry.gname = gname

            self.write_entry(archive_entry)

            with open(source_file, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    self.write_data(chunk)
            #end with
        #end with
    #end function

    def __set_filter_option(self, mod, key, val):
        m = mod.encode("utf-8") if mod is not None else None
        k = key.encode("utf-8") if key is not None else None
        v = val.encode("utf-8") if val is not None else None

        if self._c_archive_p:
            rval = lib.archive_write_set_option(
                    self._c_archive_p, m, k, v)

            if rval != STATUS_OK:
                msg = error_string(self._c_archive_p)
                raise ArchiveError(msg)
            #end if
        #end if
    #end function

#end class

class ArchiveFileReader:

    def __init__(self, filename, cmd=None, raw=False, buf_size=4096):
        self._c_archive_p = lib.archive_read_new()

        try:
            self.__init_helper(filename, cmd=cmd, raw=raw)
        except Exception:
            msg = error_string(self._c_archive_p)
            self.close()
            raise ArchiveError(msg)
        #end try
    #end function

    def __init_helper(self, filename, cmd=None, raw=False):
        if cmd:
            if lib.archive_read_support_filter_program(self._c_archive_p,
                    cmd) != STATUS_OK:
                raise Exception()
        else:
            if lib.archive_read_support_filter_all(self._c_archive_p) != \
                    STATUS_OK:
                raise Exception()
        #end if

        if raw:
            if lib.archive_read_support_format_raw(self._c_archive_p) != \
                    STATUS_OK:
                raise Exception()
            if lib.archive_read_support_format_empty(self._c_archive_p) != \
                    STATUS_OK:
                raise Exception()
        else:
            if lib.archive_read_support_format_all(self._c_archive_p) != \
                    STATUS_OK:
                raise Exception()
        #end if

        if lib.archive_read_open_filename(self._c_archive_p,
                filename.encode("utf-8"), 4096) != STATUS_OK:
            raise Exception()
    #end function

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __iter__(self):
        while True:
            archive_entry = self.next_entry()
            if archive_entry is None:
                break
            yield archive_entry
            archive_entry.free()
        #end while
    #end function

    def close(self):
        if self._c_archive_p:
            lib.archive_read_free(self._c_archive_p)
            self._c_archive_p = None
    #end function

    def next_entry(self):
        archive_entry = ArchiveEntry()

        rval = lib.archive_read_next_header2(self._c_archive_p,
                archive_entry._c_entry_p)

        if rval == STATUS_EOF:
            archive_entry.free()
            self.close()
            return None
        elif rval == STATUS_OK:
            return archive_entry
        else:
            archive_entry.free()
            raise ArchiveError(error_string(self._c_archive_p))
    #end function

    def read_data(self, size=0):
        result = []

        if size > 0:
            result = [self.__read_data(size)]
        else:
            while True:
                buf = self.__read_data(8*1024)
                if not buf:
                    break
                result.append(buf)
            #end while
        #end function

        return b"".join(result)
    #end function

    def unpack_to_disk(self, base_dir=".", strip_components=0,
            sane_file_modes=True):
        for entry in self:
            pathname = entry.pathname.strip()
            pathname = re.sub(r"^(?:\.+/+)", "", pathname)
            pathname = os.sep.join(
                [base_dir, ] + pathname.split(os.sep)[strip_components:]
            )

            if not entry.is_directory:
                os.makedirs(os.path.dirname(pathname), exist_ok=True)

            if entry.is_directory:
                if sane_file_modes:
                    entry.mode |= 0o700
                os.makedirs(pathname, exist_ok=True)
                os.chmod(pathname, entry.mode)
            elif entry.is_file:
                if sane_file_modes:
                    entry.mode |= 0o600
                with open(pathname, "wb+") as f:
                    for chunk in iter(lambda: self.read_data(4096), b""):
                        f.write(chunk)
                #end with
                os.chmod(pathname, entry.mode)
                # Assume it is sufficient to do this for files.
                os.utime(pathname, (entry.atime, entry.mtime))
            elif entry.is_symbolic_link:
                if os.path.exists(pathname):
                    os.unlink(pathname)
                os.symlink(entry.symlink, pathname)
            else:
                raise ArchiveError(
                    "Don't know how to create '%s' with special file type." %
                        entry.pathname
                )
            #end if
        #end for
    #end function

    def __read_data(self, size):
        buf = ctypes.create_string_buffer(size)

        rval = lib.archive_read_data(self._c_archive_p,
                ctypes.addressof(buf), size)
        if rval < 0:
            raise ArchiveError(error_string(self._c_archive_p))

        return buf[0:rval]
    #end function

#end class
