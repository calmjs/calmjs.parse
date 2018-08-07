Changelog
=========

1.1.0 - 2018-08-07
------------------

- Correct the implementation of line continuation in strings.  This also
  meant a change in the minify unparser so that it will continue to
  remove the line continuation sequences.  [
  `#16 <https://github.com/calmjs/calmjs.parse/issues/16>`_
  ]

- Correct the implementation of ASI (automatic semicolon insertion) by
  introducing a dedicated token type, such that the production of
  empty statement can no longer happen and that distinguishes it from
  production of statements that should not have ASI applied, such that
  incorrectly successful parsing due to this issue will no longer
  result.  [
  `#18 <https://github.com/calmjs/calmjs.parse/issues/18>`_
  `rspivak/slimit#29 <https://github.com/rspivak/slimit/issues/29>`_
  `rspivak/slimit#101 <https://github.com/rspivak/slimit/issues/101>`_
  ]

1.0.1 - 2018-04-19
------------------

- Ensure that the es5 Unparser pass on the prewalk_hooks argument in
  its constructor.
- Minor packaging fixes; also include optimization modules for ply-3.11.

1.0.0 - 2017-09-26
------------------

Full support for sourcemaps; changes that make it possible follows:

- High level read/write functionality provided by a new ``io`` module.
- There is now a ``Deferrable`` rule type for marking certain Tokens
  that need extra handling.  The support for this has changed the
  various API that deals with setting up of this.
- For support of the sourcemap generation, a number of new ruletypes
  have been added.
- The sourcemap write function had its argument order modified to
  better support the sourcepath tracking feature of input Nodes.  Its
  return value also now match the ordering of the encode_sourcemap
  function.
- The chunk types in ruletypes have been renamed, and also a new type
  called StreamFragment is introduced, so that multiple sources output
  to a single stream can be properly tracked by the source mapping
  processes.
- `rspivak/slimit#66 <https://github.com/rspivak/slimit/issues/66>`_
  should be fully supported now.

Minify printer now has ability to shorten/obfuscate identifiers:

- Provide a name obfuscation function for shortening identifiers, to
  further achieve minified output.  Note that this does not yet fully
  achieve the level of minification ``slimit`` had; future versions
  may implement this functionality as various AST transformations.
- Also provided ability to drop unneeded semicolons.

Other significant changes:

- Various changes to internal class and function names for the 1.0.0
  release.  A non exhaustive listing of changes to modules relative to
  the root of this package name as compared to previous major release
  follows:

  ``asttypes``
    - All ``slimit`` compatibility features removed.
    - ``Switch`` (the incorrect version) removed.
    - ``SwitchStatement`` -> ``Switch``
    - ``SetPropAssign`` constructor: ``parameters`` -> ``parameter``
    - ``UnaryOp`` -> ``UnaryExpr``
    - Other general deprecated features also removed.
  ``factory``
    - ``Factory`` -> ``SRFactory``
  ``visitors``
    - Removed (details follow).
  ``walkers``
    - ``visitors.generic.ReprVisitor`` -> ``walkers.ReprWalker``
  ``layouts``
    - Module was split and reorganised; the simple base ones can be
      found in ``handlers.core``, the indentation related features are
      now in ``handlers.indentation``.
  ``unparsers.base``
    - ``.default_layout_handlers`` -> ``handlers.core.default_rules``
    - ``.minimum_layout_handlers`` -> ``handlers.core.minimum_rules``
  ``unparsers.prettyprint``
    - Renamed to ``unparsers.walker``.
    - The implementation was actually standard tree walking, no
      correctly implemented visitor functions/classes were ever present.
  ``vlq``
    - ``.create_sourcemap`` -> ``sourcemap.create_sourcemap``

- Broke up the visitors class as they weren't really visitors as
  described.  The new implementations (calmjs.parse-0.9.0) were really
  walkers, so move them to that name and leave it at that.  Methods
  were also renamed to better reflect their implementation and purpose.
- Many slimit compatibility modules, classes and incorrectly implemented
  functionalities removed.
- The usage of the Python 3 ``str`` type (``unicode`` in Python 2) is
  now enforced for the parser, to avoid various failure cases where
  mismatch types occur.
- The base Node asttype has a sourcepath attribute which is to be used
  for tracking the original source of the node; if assigned, all its
  subnodes without sourcepath defined should be treated as from that
  source.
- Also provide an even higher level function for usage with streams
  through the ``calmjs.parse.io`` module.
- Semicolons and braces added as structures to be rendered.

Bug fixes:

- Functions starting with a non-word character will now always have a
  whitespace rendered before it to avoid syntax error.
- Correct an incorrect iterator usage in the walk function.
- Ensure List separators don't use the rowcol positions of a subsequent
  Elision node.
- Lexer will only report real lexer tokens on errors (ASI generated
  tokens are now dropped as they don't exist in the original source
  which results in confusing rowcol reporting).
- `rspivak/slimit#57 <https://github.com/rspivak/slimit/issues/57>`_,
  as it turns out ``'\0'`` is not considered to be octal, but is a <NUL>
  character, which the rule to parse was not actually included in the
  lexer patches that were pulled in previous to this version.
- `rspivak/slimit#75 <https://github.com/rspivak/slimit/issues/75>`_,
  Option for shadowing of names of named closures, which is now disabled
  by default (obfuscated named closures will not be shadowed by other
  obfuscated names in children).
- Expressions can no longer contain an unnamed function.

0.10.1 - 2017-08-26
-------------------

- Corrected the line number reporting for the lexer, and correct the
  propagation of that to the parser and the Node subclasses.  Fixes the
  incorrect implementation added by `moses-palmer/slimit@8f9a39c7769
  <https://github.com/moses-palmer/slimit/commit/8f9a39c7769>`_ (where
  the line numbers are tabulated incorrectly when comments are present,
  and also the yacc tracking added by `moses-palmer/slimit@6aa92d68e0
  <https://github.com/moses-palmer/slimit/commit/6aa92d68e0>`_ (where
  the custom lexer class does not provide the position attributes
  required by ply).
- Implemented bookkeeping of column numbers.
- Made other various changes to AST but for compatibility reasons (to
  not force a major semver bump) they are only enabled with a flag to
  the ES5 parser.
- Corrected a fault with how switch/case statements are handled in a way
  that may break compatibility; fixes are only enabled when flagged.
  `rspivak/slimit#94 <https://github.com/rspivak/slimit/issues/94>`_
- The repr form of Node now shows the line/col number info by default;
  the visit method of the ReprVisitor class have not been changed, only
  the invocation of it via the callable form has as that is the call
  target for __repr__.  This is a good time to mention that named
  methods afford the most control for usage as documented already.
- Parsers now accept an asttypes module during its construction.
- Provide support for source map generation classes.
- Introduced a flexible visitor function/state class that accepts a
  definition of rules for the generation of chunk tuples that are
  compatible for the source map generation.  A new way for pretty
  printing and minification can be achieved using this module.

0.9.0 - 2017-06-09
------------------

- Initial release of the fork of ``slimit.parser`` and its parent
  modules as ``calmjs.parse``.
- This release brings in a number of bug fixes that were available via
  other forks of ``slimit``, with modifications or even a complete
  revamp.
- Issues addressed includes:

  - `rspivak/slimit#52 <https://github.com/rspivak/slimit/issues/52>`_,
    `rspivak/slimit#59 <https://github.com/rspivak/slimit/issues/59>`_,
    `rspivak/slimit#81 <https://github.com/rspivak/slimit/issues/81>`_,
    `rspivak/slimit#90 <https://github.com/rspivak/slimit/issues/90>`_
    (relating to conformance of ecma-262 7.6 identifier names)
  - `rspivak/slimit#54 <https://github.com/rspivak/slimit/issues/54>`_
    (fixed by tracking scope and executable current token in lexer)
  - `rspivak/slimit#57 <https://github.com/rspivak/slimit/issues/57>`_,
    `rspivak/slimit#70 <https://github.com/rspivak/slimit/issues/70>`_
    (octal encoding (e.g \0), from `redapple/slimit@a93204577f
    <https://github.com/redapple/slimit/commit/a93204577f>`_)
  - `rspivak/slimit#62 <https://github.com/rspivak/slimit/issues/62>`_
    (formalized into a unittest that passed)
  - `rspivak/slimit#73 <https://github.com/rspivak/slimit/issues/73>`_
    (specifically the desire for a better repr; the minifier bits are
    not relevant to this package)
  - `rspivak/slimit#79 <https://github.com/rspivak/slimit/pull/79>`_
    (tab module handling was completely reimplemented)
  - `rspivak/slimit#82 <https://github.com/rspivak/slimit/issues/82>`_
    (formalized into a unittest that passed)

- Include various changes gathered by `rspivak/slimit#65
  <https://github.com/rspivak/slimit/pull/65>`_, which may be the source
  of some of the fixes listed above.
