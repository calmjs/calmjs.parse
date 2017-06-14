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

        if not isinstance(value, int):
            raise TypeError("assignment must be of type 'int'")

        if not self._hasattr(attr):
            self._curr[attr] = self._prev[attr] = value
        else:
            self._curr[attr], self._prev[attr] = value, self._curr[attr]

    def __getattr__(self, attr):
        if not self._hasattr(attr):
            raise AttributeError("'%s' object has no attribute %r" % (
                self.__class__.__name__, attr))
        return self._curr[attr] - self._prev[attr]

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
