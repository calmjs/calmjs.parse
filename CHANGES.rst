Changelog
=========

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
