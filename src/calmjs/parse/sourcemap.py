# -*- coding: utf-8 -*-
"""
Source map helpers
"""


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


def normalize_mapping_line(mapping_line):
    """
    Often times the position will remain stable, such that the naive
    process will end up with many redundant values; this function will
    iterate through the line and remove all extra values.
    """

    def regenerate(segment):
        if len(segment) == 5:
            result = (record[0], segment[1], segment[2], record[3], segment[4])
        else:
            result = (record[0], segment[1], segment[2], record[3])
        # reset the record
        record[:] = [0, 0, 0, 0]
        return result

    if not mapping_line:
        return []

    # first element
    result = [mapping_line[0]]
    # initial values
    record = [0, 0, 0, 0]
    record_next = len(mapping_line[0]) == 5
    for segment in mapping_line[1:]:
        # if the line has not changed, and that the increases of both
        # columns are the same, accumulate the column counter and drop
        # the segment.

        # accumulate the current record first
        # XXX no support for the 1-tuple segment because this is not
        # currently implemented yet
        record[0] += segment[0]
        record[3] += segment[3]

        # 5-tuples are always special case with the remapped identifier
        # name element, and to mark the termination the next token must
        # also be explicitly written (in our case, regenerated).  If the
        # filename or source line relative position changed (idx 1 and
        # 2), regenerate it too.  Finally, if the column offsets differ
        # between source and sink, regenerate.
        if len(segment) == 5 or record_next or segment[1] or segment[2] or (
                record[0] != record[3]):
            result.append(regenerate(segment))
            record_next = len(segment) == 5

    return result


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
        lines = chunk.splitlines(True)
        for line in lines:
            stream.write(line)

            # setting source_* first, as the provided values are the
            # absolute positional values
            # assume line is unchanged otherwise
            if lineno:
                book.source_line = lineno
            # assume these untagged chunks follow the previous tagged
            # chunks, so increment the column count by that previous
            # length
            book.source_column = (
                book._source_column + p_line_len if colno is None else colno)

            name_id = names.update(original_name)
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
                # TODO if this is that exceptional, log a warning?
                colno += len(line.rstrip())
                p_line_len = 0
                push_line()
            else:
                p_line_len = len(line)
                book.sink_column = book._sink_column + p_line_len

    # normalize everything
    if normalize:
        mapping = [normalize_mapping_line(ml) for ml in mapping]
    return list(names), mapping
