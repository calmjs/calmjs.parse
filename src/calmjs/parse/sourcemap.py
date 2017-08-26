# -*- coding: utf-8 -*-
"""
Source map helpers
"""

from __future__ import unicode_literals
import logging

logger = logging.getLogger(__name__)


class Names(object):
    """
    A class for tracking and reporting of names for usage with source
    maps.
    """

    def __init__(self):
        self._names = {}
        self._current = 0

    def update(self, name):
        """
        Query a name for the relative index value to be added into the
        source map name field (optional 5th element).
        """

        if name is None:
            return

        if name not in self._names:
            # add the name if it isn't already tracked
            self._names[name] = len(self._names)

        result = self._names[name] - self._current
        self._current = self._names[name]
        return result

    def __iter__(self):
        for name, idx in sorted(self._names.items(), key=lambda x: x[1]):
            yield name


class Bookkeeper(object):
    """
    A class for tracking positions

    Set a current position, read out a delta compared to the previous
    for a given attribute
    """

    def __init__(self):
        super(Bookkeeper, self).__setattr__('_prev', {})
        super(Bookkeeper, self).__setattr__('_curr', {})

    def _hasattr(self, attr):
        return all(
            isinstance(check.get(attr, None), int)
            for check in (self._prev, self._curr)
        )

    def __setattr__(self, attr, value):
        """
        Set the current position
        """

        chk = attr[:1] == '_'
        attr = attr[1:] if chk else attr

        if not isinstance(value, int):
            raise TypeError("assignment must be of type 'int'")

        if not self._hasattr(attr) or chk:
            self._curr[attr] = self._prev[attr] = value
        else:
            self._curr[attr], self._prev[attr] = value, self._curr[attr]

    def __getattr__(self, attr):
        chk = attr[:1] == '_'
        attr = attr[1:] if chk else attr
        if not self._hasattr(attr):
            raise AttributeError("'%s' object has no attribute %r" % (
                self.__class__.__name__, attr))
        return self._curr[attr] if chk else self._curr[attr] - self._prev[attr]

    def __delattr__(self, attr):
        if not self._hasattr(attr):
            raise AttributeError("'%s' object has no attribute %r" % (
                self.__class__.__name__, attr))
        self._prev[attr] = self._curr[attr] = 0


def default_book():
    book = Bookkeeper()
    # index of the current file can be implemented/tracked with the
    # Names class.

    # position of the current line that is being written; 0-indexed as
    # there are no existing requirements, and that it maps directly to
    # the length of the string written (usually).
    book.sink_column = 0
    # since the source line/col positions have been implemented as
    # 1-indexed values, so the offset is pre-applied like so.
    book.source_line = 1
    book.source_column = 1
    return book


def normalize_mapping_line(mapping_line, previous_source_column=0):
    """
    Often times the position will remain stable, such that the naive
    process will end up with many redundant values; this function will
    iterate through the line and remove all extra values.
    """

    if not mapping_line:
        return [], previous_source_column

    # Note that while the local record here is also done as a 4-tuple,
    # element 1 and 2 are never used since they are always provided by
    # the segments in the mapping line; they are defined for consistency
    # reasons.

    def regenerate(segment):
        if len(segment) == 5:
            result = (record[0], segment[1], segment[2], record[3], segment[4])
        else:
            result = (record[0], segment[1], segment[2], record[3])
        # reset the record
        # XXX this is insufficient, we need to know exactly where the
        # record is, because for pretty-printing of a long line into
        # proper indentation, this will reset the positions wrongly
        record[:] = [0, 0, 0, 0]
        return result

    # first element of the line; sink column (0th element) is always
    # the absolute value, so always use the provided value sourced from
    # the original mapping_line; the source column (3rd element) is
    # never reset, so if a previous counter exists (which is specified
    # by the optional argument), make use of it to generate the initial
    # normalized segment.
    record = [0, 0, 0, previous_source_column]
    result = []
    regen_next = True

    for segment in mapping_line:
        if not segment:
            # ignore empty records
            continue
        # if the line has not changed, and that the increases of both
        # columns are the same, accumulate the column counter and drop
        # the segment.

        # accumulate the current record first
        record[0] += segment[0]
        if len(segment) == 1:
            # Mark the termination, as 1-tuple determines the end of the
            # previous symbol and denote that whatever follows are not
            # in any previous source files.  So if it isn't recorded,
            # make note of this if it wasn't done already.
            if result and len(result[-1]) != 1:
                result.append((record[0],))
                record[0] = 0
                # the next complete segment will require regeneration
                regen_next = True
            # skip the remaining processing.
            continue

        record[3] += segment[3]

        # 5-tuples are always special case with the remapped identifier
        # name element, and to mark the termination the next token must
        # also be explicitly written (in our case, regenerated).  If the
        # filename or source line relative position changed (idx 1 and
        # 2), regenerate it too.  Finally, if the column offsets differ
        # between source and sink, regenerate.
        if len(segment) == 5 or regen_next or segment[1] or segment[2] or (
                record[0] != record[3]):
            result.append(regenerate(segment))
            regen_next = len(segment) == 5

    # must return the consumed/omitted values.
    return result, record[3]


def write(source, stream, names=None, book=None, normalize=True):
    """
    Given a source iterable, write it to the stream object by using its
    write method.  Returns a 2-tuple, where the first element is the
    mapping, second element is the list of original string references.

    Arguments:

    source
        the source iterable
    stream
        an io.IOBase compatible stream object
    names
        an Names instance; if none is provided an instance will be
        created for internal use
    book
        A Bookkeeper instance; if none is provided an instance will be
        created for internal use

    The source iterable is of this format

    A fragment tuple must contain the following

    - The string to write to the stream
    - Original starting line of the string; None if not present
    - Original starting column fo the line; None if not present
    - Original string that this fragment represents (i.e. for the case
      where this string fragment was an identifier but got mangled into
      an alternative form); use None if this was not the case.

    If multiple files are to be tracked, it is recommended to provide a
    shared Names instance.
    """

    # There was consideration to include a filename index argument, but
    # given that the line and column are *relative*, i.e. they are
    # global values that exists for the duration of the interpretation
    # of the mapping, and so it is better to have this function focus on
    # one file at a time.  A separate function can be provided to
    # generate a new tuple to replace the first one, such that it will
    # set the line/column numbers back to zero based on what is
    # available in this file, plus incrementing the index for the source
    # file itself.

    if names is None:
        names = Names()

    if book is None:
        book = default_book()

    # declare state variables and local helpers
    mapping = []

    def push_line():
        # should normalize the current line if possible.
        mapping.append([])
        book._sink_column = 0

    # finalize initial states; the most recent list (mapping[-1]) is
    # the current line
    push_line()
    # if support for multiple files are to be provided by this function,
    # this will be tracked using Names instead; setting the filename
    # index to 0 as explained previously.
    filename = 0
    p_line_len = 0

    for chunk, lineno, colno, original_name in source:
        # note that lineno/colno are assumed to be both provided or none
        # provided.
        lines = chunk.splitlines(True)
        for line in lines:
            stream.write(line)

            name_id = names.update(original_name)

            # Two separate checks are done.  As per specification, if
            # either lineno or colno are unspecified, it is assumed that
            # the segment is unmapped - append a termination (1-tuple)
            #
            # Otherwise, note that if this segment is the beginning of a
            # line, and that an implied source colno/linecol were
            # provided (i.e. value of 0), and that the string is empty,
            # it can be safely skipped, since it is an implied and
            # unmapped indentation

            if lineno is None or colno is None:
                mapping[-1].append((book.sink_column,))
            else:
                # only track lineno if specified
                if lineno:
                    book.source_line = lineno

                # if the provided colno is to be implied, calculate it
                # based on the previous line length plus the previous
                # real source column value, otherwise standard value
                # for tracking.
                if colno:
                    book.source_column = colno
                else:
                    book.source_column = book._source_column + p_line_len

                if original_name is not None:
                    mapping[-1].append((
                        book.sink_column, filename,
                        book.source_line, book.source_column,
                        name_id
                    ))
                else:
                    mapping[-1].append((
                        book.sink_column, filename,
                        book.source_line, book.source_column
                    ))

            # doing this last to update the position for the next line
            # or chunk for the relative values based on what was added
            if line[-1:] in '\r\n':
                # Note: this HAS to be an edge case and should never
                # happen, but this has the potential to muck things up.
                # Since the parent only provided the start, will need
                # to manually track the chunks internal to here.
                # This normally shouldn't happen with sane parsers
                # and lexers, but this assumes that no further symbols
                # aside from the new lines got inserted.
                colno = (
                    colno if colno in (0, None) else
                    colno + len(line.rstrip()))
                p_line_len = 0
                push_line()

                if line is not lines[-1]:
                    logger.warning(
                        'text in the generated document at line %d may be '
                        'mapped incorrectly due to trailing newline character '
                        'in provided text fragment.', len(mapping)
                    )
                    logger.info(
                        'text in source fragments should not have trailing '
                        'characters after a new line, they should be split '
                        'off into a separate fragment.'
                    )
            else:
                p_line_len = len(line)
                book.sink_column = book._sink_column + p_line_len

    # normalize everything
    if normalize:
        column = 0
        result = []
        for ml in mapping:
            new_ml, column = normalize_mapping_line(ml, column)
            result.append(new_ml)
        mapping = result
    return list(names), mapping
