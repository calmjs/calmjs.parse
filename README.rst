calmjs.parse
============

A collection of parsers and helper libraries for understanding
ECMAScript.

.. image:: https://travis-ci.org/calmjs/calmjs.parse.svg?branch=master
    :target: https://travis-ci.org/calmjs/calmjs.parse
.. image:: https://ci.appveyor.com/api/projects/status/5dj8dnu9gmj02msu/branch/master?svg=true
    :target: https://ci.appveyor.com/project/metatoaster/calmjs-parse/branch/master
.. image:: https://coveralls.io/repos/github/calmjs/calmjs.parse/badge.svg?branch=master
    :target: https://coveralls.io/github/calmjs/calmjs.parse?branch=master

.. |calmjs.parse| replace:: ``calmjs.parse``
.. |slimit| replace:: ``slimit``
.. _slimit: https://pypi.python.org/pypi/slimit

Introduction
------------

For any kind of build system that operates with JavaScript code in
conjunction with a module system, the ability to understand what modules
the provided sources require is paramount.

The core of the parsing library is a fork of the parser from |slimit|_,
a JavaScript minifier that also provided a comprehensive parser class
that was built on top of LEX & Yacc.  However, the most recent release
(0.8.1, as of mid-2017) is already four years old, and does not support
other JavaScript based minifier outputs.


Legal
-----

The |calmjs.parse| package is licensed under the MIT license
(specifically, the Expat License), which is also the same license that
the package |slimit| was released under.

The lexer, parser, visitor and the other types definitions portions were
originally imported from the |slimit| package; |slimit| is copyright (c)
Ruslan Spivak.

The Calmjs project is copyright (c) 2016 Auckland Bioengineering
Institute, University of Auckland.
