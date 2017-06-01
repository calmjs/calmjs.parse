calmjs.parse
============

A collection of parsers and helper libraries for understanding
ECMAScript.


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

The parser portion that was imported from the |slimit| library is
copyright (c) Ruslan Spivak, and is was licensed under the MIT license
(specifically the Expat License).

The Calmjs project is copyright (c) 2016 Auckland Bioengineering
Institute, University of Auckland.
