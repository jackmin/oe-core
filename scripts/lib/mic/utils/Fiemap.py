""" This module implements python API for the FIEMAP ioctl. The FIEMAP ioctl
allows to find holes and mapped areas in a file. """

# Note, a lot of code in this module is not very readable, because it deals
# with the rather complex FIEMAP ioctl. To understand the code, you need to
# know the FIEMAP interface, which is documented in the
# Documentation/filesystems/fiemap.txt file in the Linux kernel sources.

# Disable the following pylint recommendations:
#   * Too many instance attributes (R0902)
# pylint: disable=R0902

import os
import struct
import array
import fcntl
from mic.utils.misc import get_block_size

# Format string for 'struct fiemap'
_FIEMAP_FORMAT = "=QQLLLL"
# sizeof(struct fiemap)
_FIEMAP_SIZE = struct.calcsize(_FIEMAP_FORMAT)
# Format string for 'struct fiemap_extent'
_FIEMAP_EXTENT_FORMAT = "=QQQQQLLLL"
# sizeof(struct fiemap_extent)
_FIEMAP_EXTENT_SIZE = struct.calcsize(_FIEMAP_EXTENT_FORMAT)
# The FIEMAP ioctl number
_FIEMAP_IOCTL = 0xC020660B

# Minimum buffer which is required for 'class Fiemap' to operate
MIN_BUFFER_SIZE = _FIEMAP_SIZE + _FIEMAP_EXTENT_SIZE
# The default buffer size for 'class Fiemap'
DEFAULT_BUFFER_SIZE = 256 * 1024

class Error(Exception):
    """ A class for exceptions generated by this module. We currently support
    only one type of exceptions, and we basically throw human-readable problem
    description in case of errors. """
    pass

class Fiemap:
    """ This class provides API to the FIEMAP ioctl. Namely, it allows to
    iterate over all mapped blocks and over all holes. """

    def _open_image_file(self):
        """ Open the image file. """

        try:
            self._f_image = open(self._image_path, 'rb')
        except IOError as err:
            raise Error("cannot open image file '%s': %s" \
                        % (self._image_path, err))

        self._f_image_needs_close = True

    def __init__(self, image, buf_size = DEFAULT_BUFFER_SIZE):
        """ Initialize a class instance. The 'image' argument is full path to
        the file to operate on, or a file object to operate on.

        The 'buf_size' argument is the size of the buffer for 'struct
        fiemap_extent' elements which will be used when invoking the FIEMAP
        ioctl. The larger is the buffer, the less times the FIEMAP ioctl will
        be invoked. """

        self._f_image_needs_close = False

        if hasattr(image, "fileno"):
            self._f_image = image
            self._image_path = image.name
        else:
            self._image_path = image
            self._open_image_file()

        # Validate 'buf_size'
        if buf_size < MIN_BUFFER_SIZE:
            raise Error("too small buffer (%d bytes), minimum is %d bytes" \
                    % (buf_size, MIN_BUFFER_SIZE))

        # How many 'struct fiemap_extent' elements fit the buffer
        buf_size -= _FIEMAP_SIZE
        self._fiemap_extent_cnt = buf_size / _FIEMAP_EXTENT_SIZE
        self._buf_size = self._fiemap_extent_cnt * _FIEMAP_EXTENT_SIZE
        self._buf_size += _FIEMAP_SIZE

        # Allocate a mutable buffer for the FIEMAP ioctl
        self._buf = array.array('B', [0] * self._buf_size)

        self.image_size = os.fstat(self._f_image.fileno()).st_size

        try:
            self.block_size = get_block_size(self._f_image)
        except IOError as err:
            raise Error("cannot get block size for '%s': %s" \
                        % (self._image_path, err))

        self.blocks_cnt = self.image_size + self.block_size - 1
        self.blocks_cnt /= self.block_size

        # Synchronize the image file to make sure FIEMAP returns correct values
        try:
            self._f_image.flush()
        except IOError as err:
            raise Error("cannot flush image file '%s': %s" \
                        % (self._image_path, err))
        try:
            os.fsync(self._f_image.fileno()),
        except OSError as err:
            raise Error("cannot synchronize image file '%s': %s " \
                        % (self._image_path, err.strerror))

        # Check if the FIEMAP ioctl is supported
        self.block_is_mapped(0)

    def __del__(self):
        """ The class destructor which closes the opened files. """

        if self._f_image_needs_close:
            self._f_image.close()

    def _invoke_fiemap(self, block, count):
        """ Invoke the FIEMAP ioctl for 'count' blocks of the file starting from
        block number 'block'.

        The full result of the operation is stored in 'self._buf' on exit.
        Returns the unpacked 'struct fiemap' data structure in form of a python
        list (just like 'struct.upack()'). """

        if block < 0 or block >= self.blocks_cnt:
            raise Error("bad block number %d, should be within [0, %d]" \
                        % (block, self.blocks_cnt))

        # Initialize the 'struct fiemap' part of the buffer
        struct.pack_into(_FIEMAP_FORMAT, self._buf, 0, block * self.block_size,
                         count * self.block_size, 0, 0,
                         self._fiemap_extent_cnt, 0)

        try:
            fcntl.ioctl(self._f_image, _FIEMAP_IOCTL, self._buf, 1)
        except IOError as err:
            error_msg = "the FIEMAP ioctl failed for '%s': %s" \
                        % (self._image_path, err)
            if err.errno == os.errno.EPERM or err.errno == os.errno.EACCES:
                # The FIEMAP ioctl was added in kernel version 2.6.28 in 2008
                error_msg += " (looks like your kernel does not support FIEMAP)"

            raise Error(error_msg)

        return struct.unpack(_FIEMAP_FORMAT, self._buf[:_FIEMAP_SIZE])

    def block_is_mapped(self, block):
        """ This function returns 'True' if block number 'block' of the image
        file is mapped and 'False' otherwise. """

        struct_fiemap = self._invoke_fiemap(block, 1)

        # The 3rd element of 'struct_fiemap' is the 'fm_mapped_extents' field.
        # If it contains zero, the block is not mapped, otherwise it is
        # mapped.
        return bool(struct_fiemap[3])

    def block_is_unmapped(self, block):
        """ This function returns 'True' if block number 'block' of the image
        file is not mapped (hole) and 'False' otherwise. """

        return not self.block_is_mapped(block)

    def _unpack_fiemap_extent(self, index):
        """ Unpack a 'struct fiemap_extent' structure object number 'index'
        from the internal 'self._buf' buffer. """

        offset = _FIEMAP_SIZE + _FIEMAP_EXTENT_SIZE * index
        return struct.unpack(_FIEMAP_EXTENT_FORMAT,
                             self._buf[offset : offset + _FIEMAP_EXTENT_SIZE])

    def _do_get_mapped_ranges(self, start, count):
        """ Implements most the functionality for the  'get_mapped_ranges()'
        generator: invokes the FIEMAP ioctl, walks through the mapped
        extents and yields mapped block ranges. However, the ranges may be
        consecutive (e.g., (1, 100), (100, 200)) and 'get_mapped_ranges()'
        simply merges them. """

        block = start
        while block < start + count:
            struct_fiemap = self._invoke_fiemap(block, count)

            mapped_extents = struct_fiemap[3]
            if mapped_extents == 0:
                # No more mapped blocks
                return

            extent = 0
            while extent < mapped_extents:
                fiemap_extent = self._unpack_fiemap_extent(extent)

                # Start of the extent
                extent_start = fiemap_extent[0]
                # Starting block number of the extent
                extent_block = extent_start / self.block_size
                # Length of the extent
                extent_len = fiemap_extent[2]
                # Count of blocks in the extent
                extent_count = extent_len / self.block_size

                # Extent length and offset have to be block-aligned
                assert extent_start % self.block_size == 0
                assert extent_len % self.block_size == 0

                if extent_block > start + count - 1:
                    return

                first = max(extent_block, block)
                last = min(extent_block + extent_count, start + count) - 1
                yield (first, last)

                extent += 1

            block = extent_block + extent_count

    def get_mapped_ranges(self, start, count):
        """ A generator which yields ranges of mapped blocks in the file. The
        ranges are tuples of 2 elements: [first, last], where 'first' is the
        first mapped block and 'last' is the last mapped block.

        The ranges are yielded for the area of the file of size 'count' blocks,
        starting from block 'start'. """

        iterator = self._do_get_mapped_ranges(start, count)

        first_prev, last_prev = iterator.next()

        for first, last in iterator:
            if last_prev == first - 1:
                last_prev = last
            else:
                yield (first_prev, last_prev)
                first_prev, last_prev = first, last

        yield (first_prev, last_prev)

    def get_unmapped_ranges(self, start, count):
        """ Just like 'get_mapped_ranges()', but yields unmapped block ranges
        instead (holes). """

        hole_first = start
        for first, last in self._do_get_mapped_ranges(start, count):
            if first > hole_first:
                yield (hole_first, first - 1)

            hole_first = last + 1

        if hole_first < start + count:
            yield (hole_first, start + count - 1)
