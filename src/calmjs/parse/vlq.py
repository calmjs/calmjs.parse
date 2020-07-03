# -*- coding: utf-8 -*-
"""
Module for dealing with VLQ encodings
"""

# While base64 is used, it's not used for the string encoding but the
# characters map to corresponding bits.  The lowest 5 bits map to the
# actual number, with the highest (6th) bit being the continuation mark;
# if set, denote the next character is to build on the current.  Do note
# that a given set of bits, the lowest bit is the sign bit; if set, the
# number is negative.
#
# Examples:  (c = continuation bit, s = negative sign bit)
#
# (A) A is 0th char               (E) E is 5th char
# A | c - - - - s |               E | c - - - - s |
# 0 | 0 0 0 0 0 0 | = 0           5 | 0 0 0 1 0 0 | = 2
#
# (F) F has sign bit, negative   (2H) 2 has continuation bit, H does not
# F | c - - - - s |             2 H | c - - - - s | c - - - - - |
# 0 | 0 0 0 1 0 1 | = -2       54 7 | 1 1 0 1 1 0 | 0 0 0 1 1 1 | = 123
#
# For the 2H example, note that it's only the `2` character that carry
# the sign bit as it has the lowest bit, the other characters form
# further higher bits until the last one without one.  The bits would
# look like ( 0 0 1 1 1 | 1 0 1 1 + ) for the conversion to the interger
# value of +123.
#
# Thus arbitrary long integers can be represented by arbitrary long
# string of the following 64 characters.  In the source map case, each
# character that has no continuation bit marks the end of the current
# element, following characters form the next element in the list of
# integers that describes a given line in the mapped file.  Each line in
# the mapped file (which is typically the generated artifact) has a
# corresponding line in the mapping denoted by the number of semicolons
# before it (0th line has no semicolons in front of the list of integers
# encoded in VLQ).  Each of these lines are broken into segments of
# either 1, 4 or 5 tuple of integers encoded in VLQ, delimited by commas
# for all the segments within the line that maps to the original source
# file.
#
# For full details please consult the source map v3 specification.

INT_B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
B64_INT = dict((c, i) for i, c in enumerate(INT_B64))

# smallest number that need two characters
VLQ_MULTI_CHAR = 16

# for bit shifting
VLQ_SHIFT = 5

# 100000 = 32, since we have two sets of representation of 16, ignoring
# the bit sign; also for the continuation
VLQ_CONT = VLQ_BASE = 1 << VLQ_SHIFT

# 111111
VLQ_CONT_MASK = 63

# 011111
VLQ_BASE_MASK = 31


def encode_vlq(i):
    """
    Encode integer `i` into a VLQ encoded string.
    """

    # shift in the sign to least significant bit
    raw = (-i << 1) + 1 if i < 0 else i << 1
    if raw < VLQ_MULTI_CHAR:
        # short-circuit simple case as it doesn't need continuation
        return INT_B64[raw]

    result = []
    while raw:
        # assume continue
        result.append(raw & VLQ_BASE_MASK | VLQ_CONT)
        # shift out processed bits
        raw = raw >> VLQ_SHIFT
    # discontinue the last unit
    result[-1] &= VLQ_BASE_MASK
    return ''.join(INT_B64[i] for i in result)


def encode_vlqs(ints):
    return ''.join(encode_vlq(i) for i in ints)


def vlq_decoder(s):
    """
    A generator that accepts a VLQ encoded string as input to produce
    integers.
    """

    i = 0
    shift = 0

    for c in s:
        raw = B64_INT[c]
        cont = VLQ_CONT & raw
        i = ((VLQ_BASE_MASK & raw) << shift) | i
        shift += VLQ_SHIFT
        if not cont:
            sign = -1 if 1 & i else 1
            yield (i >> 1) * sign
            i = 0
            shift = 0


def decode_vlq(s):
    """
    Decode the first integer from a vlq encoded string.
    """

    return next(vlq_decoder(s))


def decode_vlqs(s):
    """
    Decode str `s` into a tuple of integers.
    """

    return tuple(vlq_decoder(s))


def encode_mappings(mappings):
    def encode_line(line):
        return ','.join(encode_vlqs(frags) for frags in line)
    return ';'.join(encode_line(line) for line in mappings)


def decode_mappings(mappings_str):
    def decode_line(line):
        return list(decode_vlqs(frags) for frags in line.split(',') if frags)
    return list(decode_line(line) for line in mappings_str.split(';'))
