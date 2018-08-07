calmjs.parse
============

A collection of parsers and helper libraries for understanding
ECMAScript; a near feature complete fork of |slimit|_.  A CLI front-end
for this package is shipped separately as |crimp|_.

.. image:: https://travis-ci.org/calmjs/calmjs.parse.svg?branch=1.1.0
    :target: https://travis-ci.org/calmjs/calmjs.parse
.. image:: https://ci.appveyor.com/api/projects/status/5dj8dnu9gmj02msu/branch/1.1.0?svg=true
    :target: https://ci.appveyor.com/project/metatoaster/calmjs-parse/branch/1.1.0
.. image:: https://coveralls.io/repos/github/calmjs/calmjs.parse/badge.svg?branch=1.1.0
    :target: https://coveralls.io/github/calmjs/calmjs.parse?branch=1.1.0

.. |calmjs.parse| replace:: ``calmjs.parse``
.. |crimp| replace:: ``crimp``
.. |ply| replace:: ``ply``
.. |slimit| replace:: ``slimit``
.. _crimp: https://pypi.python.org/pypi/crimp
.. _ply: https://pypi.python.org/pypi/ply
.. _slimit: https://pypi.python.org/pypi/slimit


Introduction
------------

For any kind of build system that operates with JavaScript code in
conjunction with a module system, the ability to understand what modules
a given set of sources require or provide is paramount.  As the Calmjs
project provides a framework that produces and consume these module
definitions, the the ability to have a comprehensive understanding of
given JavaScript sources is a given.  This goal was originally achieved
using |slimit|_, a JavaScript minifier library that also provided a
comprehensive parser class that was built using Python Lex-Yacc (i.e.
|ply|_).

However, as of mid-2017, it was noted that |slimit| remained in a
minimum state of maintenance for more than four years (its most recent
release, 0.8.1, was made 2013-03-26), along with a number of serious
outstanding issues have left unattended and unresolved for the duration
of that time span.  As the development of the Calmjs framework require
those issues to be rectified as soon as possible, a decision to fork the
parser portion of |slimit| was made. This was done in order to cater to
the interests current to Calmjs project at that moment in time.

The fork was initial cut from another fork of |slimit| (specifically
`lelit/slimit <https://github.com/lelit/slimit>`_), as it introduced and
aggregated a number of bug fixes from various sources.  To ensure a
better quality control and assurance, a number of problematic changes
introduced by that fork were removed.   Also, new tests were created to
bring coverage to full, and issues reported on the |slimit| tracker were
noted and formalized into test cases where applicable.  Finally, grammar
rules were updated to ensure better conformance with the ECMA-262 (ES5)
specification.

The goal of |calmjs.parse| is to provide a similar API that |slimit| had
provided, except done in a much more extensible manner with more
correctness checks in place.  This however resulted in some operations
that might take longer than what |slimit| had achieved, such as the
pretty printing of output.

A CLI front-end that makes use of this package is provided through
|crimp|_.


Installation
------------

The following command may be executed to source the latest stable
version of |calmjs.parse| wheel from PyPI for installation into the
current Python environment.

.. code:: sh

    $ pip install calmjs.parse

As this package uses |ply|, it requires the generation of optimization
modules for its lexer.  The wheel distribution of |calmjs.parse| does
not require this extra step as it contains these pre-generated modules
for |ply| up to version 3.11 (the latest version available at the time
of previous release), however the source tarball or if |ply| version
that is installed lies outside of the supported versions, the following
caveats will apply.

If a more recent release of |ply| becomes available and the environment
upgrades to that version, those pre-generated modules may become
incompatible, which may result in a decreased performance and/or errors.
A corrective action can be achieved through a `manual optimization`_
step if a newer version of |calmjs.parse| is not available, or |ply| may
be downgraded back to version 3.11 if possible.

Once the package is installed, the installation may be `tested`_ or be
`used directly`_.

Alternative installation methods (for developers, advanced users)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Development is still ongoing with |calmjs.parse|, for the latest
features and bug fixes, the development version may be installed through
git like so:

.. code:: sh

    $ pip install git+https://github.com/calmjs/calmjs.parse.git#egg=calmjs.parse

Alternatively, the git repository can be cloned directly and execute
``python setup.py develop`` while inside the root of the source
directory.

A manual optimization step may need to be performed for platforms and
systems that do not have utf8 as their default encoding.

Manual optimization
~~~~~~~~~~~~~~~~~~~

As lex and yacc require the generation of symbol tables, a way to
optimize the performance is to cache the results.  For |ply|, this is
done using an auto-generated module.  However, the generated file is
marked with a version number, as the results may be specific to the
installed version of |ply|.  In |calmjs.parse| this is handled by giving
them a name specific to the version of |ply| and the major Python
version, as both together does result in subtle differences in the
outputs and expectations of the auto-generated modules.

Typically, the process for this optimization is automatic and a correct
symbol table will be generated, however there are cases where this will
fail, so for this reason |calmjs.parse| provide a helper module and
executable that can be optionally invoked to ensure that the correct
encoding be used to generate that file.  Other reasons where this may be
necessary is to allow system administrators to do so for their end
users, as they may not have write privileges at that level.

To execute the optimizer from the shell, the provided helper script may
be used like so:

.. code:: sh

    $ python -m calmjs.parse.parsers.optimize

If warnings appear that warn that tokens are defined but not used, they
may be safely ignored.

This step is generally optionally for users who installed this package
from PyPI via a Python wheel, provided the caveats as outlined in the
installation section are addressed.

.. _tested:

Testing the installation
~~~~~~~~~~~~~~~~~~~~~~~~

To ensure that the |calmjs.parse| installation is functioning correctly,
the built-in testsuite can be executed by the following:

.. code:: sh

    $ python -m unittest calmjs.parse.tests.make_suite

If there are failures, please file an issue on the `issue tracker
<https://github.com/calmjs/calmjs.parse/issues>`_ with the full
traceback, and/or the method of installation.  Please also include
applicable information about the environment, such as the version of
this software, Python version, operating system environments, the
version of |ply| that was installed, plus other information related to
the issue at hand.


Usage
-----

.. _used directly:

As this is a parser library, no executable shell commands are provided.
There is however a helper callable object provided at the top level for
immediate access to the parsing feature.  It may be used like so:

.. code:: python

    >>> from calmjs.parse import es5
    >>> program_source = u'''
    ... // simple program
    ... var main = function(greet) {
    ...     var hello = "hello " + greet;
    ...     return hello;
    ... };
    ... console.log(main('world'));
    ... '''
    >>> program = es5(program_source)
    >>> # for a simple repr-like nested view of the ast
    >>> program  # equivalent to repr(program)
    <ES5Program @3:1 ?children=[
      <VarStatement @3:1 ?children=[
        <VarDecl @3:5 identifier=<Identifier ...>, initializer=<FuncExpr ...>>
      ]>,
      <ExprStatement @7:1 expr=<FunctionCall @7:1 args=<Arguments ...>,
        identifier=<DotAccessor ...>>>
    ]>
    >>> # automatic reconstruction of ast into source, without having to
    >>> # call something like `.to_ecma()`
    >>> print(program)  # equivalent to str(program)
    var main = function(greet) {
      var hello = "hello " + greet;
      return hello;
    };
    console.log(main('world'));

    >>>

Please note the change in indentation and the lack of comments, as the
default printer has its own indentation scheme and the parser currently
skips over comments.

The parser classes are organized under the ``calmjs.parse.parsers``
module, with each language being under their own module.  A
corresponding lexer class with the same name is also provided under the
``calmjs.parse.lexers`` module.  For the moment, only ES5 support is
implemented.

Pretty/minified printing
~~~~~~~~~~~~~~~~~~~~~~~~

There is also a set of pretty printing helpers for turning the AST back
into a string.  These are available as functions or class constructors,
and are produced by composing various lower level classes available in
the ``calmjs.parse.unparsers`` and related modules.

There is a default short-hand helper for turning the previously produced
AST back into a string, which can be manually invoked with certain
parameters, such as what characters to use for indentation: (note that
the ``__str__`` call implicitly invoked through ``print`` shown
previously is implemented through this).

.. code:: python

    >>> from calmjs.parse.unparsers.es5 import pretty_print
    >>> print(pretty_print(program, indent_str='    '))
    var main = function(greet) {
        var hello = "hello " + greet;
        return hello;
    };
    console.log(main('world'));

    >>>

There is also one for printing without any unneeded whitespaces, works
as a source minifier:

.. code:: python

    >>> from calmjs.parse.unparsers.es5 import minify_print
    >>> print(minify_print(program))
    var main=function(greet){var hello="hello "+greet;return hello;};...
    >>> print(minify_print(program, obfuscate=True, obfuscate_globals=True))
    var a=function(b){var a="hello "+b;return a;};console.log(a('world'));

Note that in the second example, the ``obfuscate_globals`` option was
only enabled to demonstrate the source obfuscation on the global scope,
and this is generally not an option that should be enabled on production
library code that is meant to be reused by other packages (other sources
referencing the original unobfuscated names will be unable to do so).

Alternatively, direct invocation on a raw string can be done using the
attributes that were provided under the same name as the base object that
was imported initially.  For instance, it can simply pretty print a
JavaScript source file without comments, or minify the source file
directly.

.. code:: python

    >>> print(es5.pretty_print(program_source))
    var main = function(greet) {
      var hello = "hello " + greet;
      return hello;
    };
    console.log(main('world'));

    >>> print(es5.minify_print(program_source, obfuscate=True))
    var main=function(b){var a="hello "+b;return a;};console.log(main('world'));

Source map generation
~~~~~~~~~~~~~~~~~~~~~

For the generation of source maps, a lower level unparser instance can
be constructed through one of the printer factory functions.  Passing
in an AST node will produce a generator which produces tuples containing
the yielded text fragment, plus other information which will aid in the
generation of source maps.  There are helper functions from the
``calmjs.parse.sourcemap`` module can be used like so to write the
regenerated source code to some stream, along with processing the
results into a sourcemap file.  An example:

.. code:: python

    >>> import json
    >>> from io import StringIO
    >>> from calmjs.parse.unparsers.es5 import pretty_printer
    >>> from calmjs.parse.sourcemap import encode_sourcemap, write
    >>> stream_p = StringIO()
    >>> print_p = pretty_printer()
    >>> rawmap_p, _, names_p = write(print_p(program), stream_p)
    >>> sourcemap_p = encode_sourcemap(
    ...     'demo.min.js', rawmap_p, ['custom_name.js'], names_p)
    >>> print(json.dumps(sourcemap_p, indent=2, sort_keys=True))
    {
      "file": "demo.min.js",
      "mappings": "AAEA;IACI;IACA;AACJ;AACA;",
      "names": [],
      "sources": [
        "custom_name.js"
      ],
      "version": 3
    }
    >>> print(stream_p.getvalue())
    var main = function(greet) {
    ...

Likewise, this works similarly for the minify printer, which provides
the ability to create out a minified output with unneeded whitespaces
removed and identifiers obfuscated with the shortest possible value.

Note that in previous example, the second return value in the write
method was not used and that a custom value was passed in.  This is
simply due to how the ``program`` was generated from a string and thus
the ``sourcepath`` attribute was not assigned with a usable value for
populating the ``"sources"`` list in the resulting source map.  For the
following example, assign a value to that attribute on the program
directly.

.. code:: python

    >>> from calmjs.parse.unparsers.es5 import minify_printer
    >>> program.sourcepath = 'demo.js'  # say this was opened there
    >>> stream_m = StringIO()
    >>> print_m = minify_printer(obfuscate=True, obfuscate_globals=True)
    >>> sourcemap_m = encode_sourcemap(
    ...     'demo.min.js', *write(print_m(program), stream_m))
    >>> print(json.dumps(sourcemap_m, indent=2, sort_keys=True))
    {
      "file": "demo.min.js",
      "mappings": "AAEA,IAAIA,CAAK,CAAE,SAASC,CAAK,CAAE,CACvB,...,YAAYF,CAAI",
      "names": [
        "main",
        "greet",
        "hello"
      ],
      "sources": [
        "demo.js"
      ],
      "version": 3
    }
    >>> print(stream_m.getvalue())
    var a=function(b){var a="hello "+b;return a;};console.log(a('world'));

A high level API for working with named streams (i.e. opened files, or
stream objects like ``io.StringIO`` assigned with a name attribute) is
provided by the ``read`` and ``write`` functions from ``io`` module.
The following example shows how to use the function to read from a
stream and write out the relevant items back out to the write only
streams:

.. code:: python

    >>> from calmjs.parse import io
    >>> h4_program_src = open('/tmp/html4.js')
    >>> h4_program_min = open('/tmp/html4.min.js', 'w+')
    >>> h4_program_map = open('/tmp/html4.min.js.map', 'w+')
    >>> h4_program = io.read(es5, h4_program_src)
    >>> print(h4_program)
    var bold = function(s) {
      return '<b>' + s + '</b>';
    };
    var italics = function(s) {
      return '<i>' + s + '</i>';
    };
    >>> io.write(print_m, h4_program, h4_program_min, h4_program_map)
    >>> pos = h4_program_map.seek(0)
    >>> print(h4_program_map.read())
    {"file": "html4.min.js", "mappings": ..., "version": 3}
    >>> pos = h4_program_min.seek(0)
    >>> print(h4_program_min.read())
    var b=function(a){return'<b>'+a+'</b>';};var a=function(a){...};
    //# sourceMappingURL=html4.min.js.map

For a simple concatenation of multiple sources into one file, along with
inline source map (i.e. where the sourceMappingURL is a ``data:`` URL of
the base64 encoding of the JSON string), the following may be done:

.. code:: python

    >>> files = [open('/tmp/html4.js'), open('/tmp/legacy.js')]
    >>> combined = open('/tmp/combined.js', 'w+')
    >>> io.write(print_p, (io.read(es5, f) for f in files), combined, combined)
    >>> pos = combined.seek(0)
    >>> print(combined.read())
    var bold = function(s) {
        return '<b>' + s + '</b>';
    };
    var italics = function(s) {
        return '<i>' + s + '</i>';
    };
    var marquee = function(s) {
        return '<marquee>' + s + '</marquee>';
    };
    var blink = function(s) {
        return '<blink>' + s + '</blink>';
    };
    //# sourceMappingURL=data:application/json;base64;...

In this example, the ``io.write`` function was provided with the pretty
unparser, an generator expression that will produce the two ASTs from
the two source files, and then both the target and sourcemap argument
are identical, which forces the source map generator to generate the
base64 encoding.

Do note that if multiple ASTs were supplied to a minifying printer with
globals being obfuscated, the resulting script will have the earlier
obfuscated global names mangled by later ones, as the unparsing is done
separately by the ``io.write`` function.


Advanced usage
--------------

Lower level unparsing API
~~~~~~~~~~~~~~~~~~~~~~~~~

Naturally, the printers demonstrated previously are constructed using
the underlying Unparser class, which in turn bridges together the walk
function and the Dispatcher class found in the walker module.  The walk
function walks through the AST node with an instance of the Dispatcher
class, which provides a description of all node types for the particular
type of AST node provided, along with the relevant handlers.  These
handlers can be set up using existing rule provider functions.  For
instance, a printer for obfuscating identifier names while maintaining
indentation for the output of an ES5 AST can be constructed like so:

.. code:: python

    >>> from calmjs.parse.unparsers.es5 import Unparser
    >>> from calmjs.parse.rules import indent
    >>> from calmjs.parse.rules import obfuscate
    >>> pretty_obfuscate = Unparser(rules=(
    ...     # note that indent must come after, so that the whitespace
    ...     # handling rules by indent will shadow over the minimum set
    ...     # provided by obfuscate.
    ...     obfuscate(obfuscate_globals=False),
    ...     indent(indent_str='    '),
    ... ))
    >>> math_module = es5(u'''
    ... (function(root) {
    ...   var fibonacci = function(count) {
    ...     if (count < 2)
    ...       return count;
    ...     else
    ...       return fibonacci(count - 1) + fibonacci(count - 2);
    ...   };
    ...
    ...   var factorial = function(n) {
    ...     if (n < 1)
    ...       throw new Error('factorial where n < 1 not supported');
    ...     else if (n == 1)
    ...       return 1;
    ...     else
    ...       return n * factorial(n - 1);
    ...   }
    ...
    ...   root.fibonacci = fibonacci;
    ...   root.factorial = factorial;
    ... })(window);
    ...
    ... var value = window.factorial(5) / window.fibonacci(5);
    ... console.log('the value is ' + value);
    ... ''')
    >>> print(''.join(c.text for c in pretty_obfuscate(math_module)))
    (function(b) {
        var a = function(b) {
            if (b < 2) return b;
            else return a(b - 1) + a(b - 2);
        };
        var c = function(a) {
            if (a < 1) throw new Error('factorial where n < 1 not supported');
            else if (a == 1) return 1;
            else return a * c(a - 1);
        };
        b.fibonacci = a;
        b.factorial = c;
    })(window);
    var value = window.factorial(5) / window.fibonacci(5);
    console.log('the value is ' + value);

Each of the rules (functions) have specific options that are set using
specific keyword arguments, details are documented in their respective
docstrings.

Tree walking
~~~~~~~~~~~~

AST (Abstract Syntax Tree) generic walker classes are defined under the
appropriate named modules ``calmjs.parse.walkers``.  Two default walker
classes are supplied.  One of them is the ``ReprWalker`` class which was
previously demonstrated.  The other is the ``Walker`` class, which
supplies a collection of generic tree walking methods for a tree of AST
nodes.  The following is an example usage on how one might extract all
Object assignments from a given script file:

.. code:: python

    >>> from calmjs.parse import es5
    >>> from calmjs.parse.asttypes import Object, VarDecl, FunctionCall
    >>> from calmjs.parse.walkers import Walker
    >>> walker = Walker()
    >>> declarations = es5(u'''
    ... var i = 1;
    ... var s = {
    ...     a: "test",
    ...     o: {
    ...         v: "value"
    ...     }
    ... };
    ... foo({foo: "bar"});
    ... function bar() {
    ...     var t = {
    ...         foo: "bar",
    ...     };
    ...     return t;
    ... }
    ... foo.bar = bar;
    ... foo.bar();
    ... ''')
    >>> # print out the object nodes that were part of some assignments
    >>> for node in walker.filter(declarations, lambda node: (
    ...         isinstance(node, VarDecl) and
    ...         isinstance(node.initializer, Object))):
    ...     print(node.initializer)
    ...
    {
      a: "test",
      o: {
        v: "value"
      }
    }
    {
      foo: "bar"
    }
    >>> # print out all function calls
    >>> for node in walker.filter(declarations, lambda node: (
    ...         isinstance(node, FunctionCall))):
    ...     print(node.identifier)
    ...
    foo
    foo.bar

Further details and example usage can be consulted from the various
docstrings found within the module.


Troubleshooting
---------------

Instantiation of parser classes fails with ``UnicodeEncodeError``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For platforms or systems that do not have utf8 configured as the default
encoding, the automatic table generation may fail when constructing a
parser instance.  An example:

.. code::

    >>> from calmjs.parse.parsers import es5
    >>> parser = es5.Parser()
    Traceback (most recent call last):
      ...
      File "c:\python35\....\ply\lex.py", line 1043, in lex
        lexobj.writetab(lextab, outputdir)
      File "c:\python35\....\ply\lex.py", line 195, in writetab
        tf.write('_lexstatere   = %s\n' % repr(tabre))
      File "c:\python35\lib\encodings\cp1252.py", line 19, in encode
        return codecs.charmap_encode(input,self.errors,encoding_table)[0]
    UnicodeEncodeError: 'charmap' codec can't encode character '\u02c1' ...

A workaround helper script is provided, it may be executed like so:

.. code:: sh

    $ python -m calmjs.parse.parsers.optimize

Further details on this topic may be found in the `manual optimization`_
section of this document.

Slow performance
~~~~~~~~~~~~~~~~

As this program is basically fully decomposed into very small functions,
this result in massive performance penalties as compared to other
implementations due to function calls being one of the most expensive
operations in Python.  It may be possible to further optimize the
definitions within the description in the Dispatcher by combining all
the resolved generator functions for each asttype Node type, however
this will may require both the token and layout functions not having
arguments with name collisions, and the new function will take in all
of those arguments in one go.


Contribute
----------

- Issue Tracker: https://github.com/calmjs/calmjs.parse/issues
- Source Code: https://github.com/calmjs/calmjs.parse


Legal
-----

The |calmjs.parse| package is copyright (c) 2017 Auckland Bioengineering
Institute, University of Auckland.  The |calmjs.parse| package is
licensed under the MIT license (specifically, the Expat License), which
is also the same license that the package |slimit| was released under.

The lexer, parser and the other types definitions portions were
originally imported from the |slimit| package; |slimit| is copyright (c)
Ruslan Spivak.

The Calmjs project is copyright (c) 2017 Auckland Bioengineering
Institute, University of Auckland.
