Changelog
=========

0.9.1 - Unreleased
------------------

- Corrected the line number reporting for the lexer, and correct the
  propagation of that to the parser and the Node subclasses.  Fixes the
  incorrect implementation added by `moses-palmer/slimit@8f9a39c7769
  <https://github.com/moses-palmer/slimit/commit/8f9a39c7769>`_ (where
  the line numbers are tabulated incorrectly when comments are present,
  and also the yacc tracking added by `moses-palmer/slimit@6aa92d68e0
  <https://github.com/moses-palmer/slimit/commit/6aa92d68e0>`_ (where
  the custom lexer class does not provide the position attributes
  required by ply).
- Implemented bookkeeping of column number.
- The repr form of Node now shows the line/col number info by default;
  the visit method of the ReprVisitor class have not been changed, only
  the invocation of it via the callable form has as that is the call
  target for __repr__.  This is a good time to mention that named
  methods afford the most control for usage as documented already.

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
