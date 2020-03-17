# -*- coding: utf-8 -*-
"""
Collection of raw lexer test cases and class constructor.
"""

from __future__ import unicode_literals

import textwrap

swapquotes = {
    39: 34, 34: 39,
    # note the follow are interim error messages
    96: 39,
}

# The structure and some test cases are taken
# from https://bitbucket.org/ned/jslex
es5_cases = [
    (
        # Identifiers
        'identifiers_ascii',
        ('i my_variable_name c17 _dummy $str $ _ CamelCase class2type',
         ['ID i', 'ID my_variable_name', 'ID c17', 'ID _dummy',
          'ID $str', 'ID $', 'ID _', 'ID CamelCase', 'ID class2type']
         ),
    ), (
        'identifiers_unicode',
        (u'\u03c0 \u03c0_tail var\ua67c',
         [u'ID \u03c0', u'ID \u03c0_tail', u'ID var\ua67c']),
    ), (
        # https://github.com/rspivak/slimit/issues/2
        'slimit_issue_2',
        ('nullify truelie falsepositive',
         ['ID nullify', 'ID truelie', 'ID falsepositive']),

    ), (
        'keywords_break',
        ('break Break BREAK', ['BREAK break', 'ID Break', 'ID BREAK']),
    ), (
        # Literals
        'literals',
        ('null true false Null True False',
         ['NULL null', 'TRUE true', 'FALSE false',
          'ID Null', 'ID True', 'ID False']
         ),
    ), (
        # Punctuators
        'punctuators_simple',
        ('a /= b', ['ID a', 'DIVEQUAL /=', 'ID b']),
    ), (
        'punctuators_various_equality',
        (('= == != === !== < > <= >= || && ++ -- << >> '
          '>>> += -= *= <<= >>= >>>= &= %= ^= |='),
         ['EQ =', 'EQEQ ==', 'NE !=', 'STREQ ===', 'STRNEQ !==', 'LT <',
          'GT >', 'LE <=', 'GE >=', 'OR ||', 'AND &&', 'PLUSPLUS ++',
          'MINUSMINUS --', 'LSHIFT <<', 'RSHIFT >>', 'URSHIFT >>>',
          'PLUSEQUAL +=', 'MINUSEQUAL -=', 'MULTEQUAL *=', 'LSHIFTEQUAL <<=',
          'RSHIFTEQUAL >>=', 'URSHIFTEQUAL >>>=', 'ANDEQUAL &=', 'MODEQUAL %=',
          'XOREQUAL ^=', 'OREQUAL |=',
          ]
         ),
    ), (
        'punctuators_various_others',
        ('. , ; : + - * % & | ^ ~ ? ! ( ) { } [ ]',
         ['PERIOD .', 'COMMA ,', 'SEMI ;', 'COLON :', 'PLUS +', 'MINUS -',
          'MULT *', 'MOD %', 'BAND &', 'BOR |', 'BXOR ^', 'BNOT ~',
          'CONDOP ?', 'NOT !', 'LPAREN (', 'RPAREN )', 'LBRACE {', 'RBRACE }',
          'LBRACKET [', 'RBRACKET ]']
         ),
    ), (
        'division_simple',
        ('a / b', ['ID a', 'DIV /', 'ID b']),
    ), (
        'numbers',
        (('3 3.3 0 0. 0.0 0.001 010 3.e2 3.e-2 3.e+2 3E2 3E+2 3E-2 '
          '0.5e2 0.5e+2 0.5e-2 33 128.15 0x001 0X12ABCDEF 0xabcdef'),
         ['NUMBER 3', 'NUMBER 3.3', 'NUMBER 0', 'NUMBER 0.', 'NUMBER 0.0',
          'NUMBER 0.001', 'NUMBER 010', 'NUMBER 3.e2', 'NUMBER 3.e-2',
          'NUMBER 3.e+2', 'NUMBER 3E2', 'NUMBER 3E+2', 'NUMBER 3E-2',
          'NUMBER 0.5e2', 'NUMBER 0.5e+2', 'NUMBER 0.5e-2', 'NUMBER 33',
          'NUMBER 128.15', 'NUMBER 0x001', 'NUMBER 0X12ABCDEF',
          'NUMBER 0xabcdef']
         ),
    ), (
        'strings_simple_quote',
        (""" '"' """, ["""STRING '"'"""]),
    ), (
        'strings_escape_quote_tab',
        (r'''"foo" 'foo' "x\";" 'x\';' "foo\tbar"''',
         ['STRING "foo"', """STRING 'foo'""", r'STRING "x\";"',
          r"STRING 'x\';'", r'STRING "foo\tbar"']
         ),
    ), (
        'strings_escape_ascii',
        (r"""'\x55' "\x12ABCDEF" '!@#$%^&*()_+{}[]\";?'""",
         [r"STRING '\x55'", r'STRING "\x12ABCDEF"',
          r"STRING '!@#$%^&*()_+{}[]\";?'"]
         ),
    ), (
        'strings_escape_unicode',
        (r"""'\u0001' "\uFCEF" 'a\\\b\n'""",
         [r"STRING '\u0001'", r'STRING "\uFCEF"', r"STRING 'a\\\b\n'"]
         ),
    ), (
        'strings_unicode',
        (u'"тест строки\\""', [u'STRING "тест строки\\""']),
    ), (
        'strings_escape_octal',
        (r"""'\251'""", [r"""STRING '\251'"""]),
    ), (
        # Bug - https://github.com/rspivak/slimit/issues/5
        'slimit_issue_5',
        (r"var tagRegExp = new RegExp('<(\/*)(FooBar)', 'gi');",
         ['VAR var', 'ID tagRegExp', 'EQ =',
          'NEW new', 'ID RegExp', 'LPAREN (',
          r"STRING '<(\/*)(FooBar)'", 'COMMA ,', "STRING 'gi'",
          'RPAREN )', 'SEMI ;']),
    ), (
        # same as above but inside double quotes
        'slimit_issue_5_double_quote',
        (r'"<(\/*)(FooBar)"', [r'STRING "<(\/*)(FooBar)"']),
    ), (
        # multiline string (string written across multiple lines
        # of code) https://github.com/rspivak/slimit/issues/24
        'slimit_issue_24_multi_line_code_double',
        ("var a = 'hello \\\n world'",
         ['VAR var', 'ID a', 'EQ =', "STRING 'hello \\\n world'"]),
    ), (
        'slimit_issue_24_multi_line_code_single',
        ('var a = "hello \\\r world"',
         ['VAR var', 'ID a', 'EQ =', 'STRING "hello \\\r world"']),
    ), (
        # regex
        'regex_1',
        (r'a=/a*/,1', ['ID a', 'EQ =', 'REGEX /a*/', 'COMMA ,', 'NUMBER 1']),
    ), (
        'regex_2',
        (r'a=/a*[^/]+/,1',
         ['ID a', 'EQ =', 'REGEX /a*[^/]+/', 'COMMA ,', 'NUMBER 1']
         ),
    ), (
        'regex_3',
        (r'a=/a*\[^/,1',
         ['ID a', 'EQ =', r'REGEX /a*\[^/', 'COMMA ,', 'NUMBER 1']
         ),
    ), (
        'regex_4',
        (r'a=/\//,1', ['ID a', 'EQ =', r'REGEX /\//', 'COMMA ,', 'NUMBER 1']),
    ), (
        # not a regex, just a division
        # https://github.com/rspivak/slimit/issues/6
        'slimit_issue_6_not_regex_but_division',
        (r'x = this / y;',
         ['ID x', 'EQ =', 'THIS this', r'DIV /', r'ID y', r'SEMI ;']),
    ), (
        'regex_mozilla_example_1',
        # next two are from
        # http://www.mozilla.org/js/language/js20-2002-04/rationale/syntax.html#regular-expressions
        ('for (var x = a in foo && "</x>" || mot ? z:/x:3;x<5;y</g/i) '
         '{xyz(x++);}',
         ["FOR for", "LPAREN (", "VAR var", "ID x", "EQ =", "ID a", "IN in",
          "ID foo", "AND &&", 'STRING "</x>"', "OR ||", "ID mot", "CONDOP ?",
          "ID z", "COLON :", "REGEX /x:3;x<5;y</g", "DIV /", "ID i",
          "RPAREN )", "LBRACE {", "ID xyz", "LPAREN (", "ID x", "PLUSPLUS ++",
          "RPAREN )", "SEMI ;", "RBRACE }"]
         ),
    ), (
        'regex_mozilla_example_2',
        ('for (var x = a in foo && "</x>" || mot ? z/x:3;x<5;y</g/i) '
         '{xyz(x++);}',
         ["FOR for", "LPAREN (", "VAR var", "ID x", "EQ =", "ID a", "IN in",
          "ID foo", "AND &&", 'STRING "</x>"', "OR ||", "ID mot", "CONDOP ?",
          "ID z", "DIV /", "ID x", "COLON :", "NUMBER 3", "SEMI ;", "ID x",
          "LT <", "NUMBER 5", "SEMI ;", "ID y", "LT <", "REGEX /g/i",
          "RPAREN )", "LBRACE {", "ID xyz", "LPAREN (", "ID x", "PLUSPLUS ++",
          "RPAREN )", "SEMI ;", "RBRACE }"]
         ),

    ), (
        'regex_illegal_1',
        # Various "illegal" regexes that are valid according to the std.
        (r"""/????/, /++++/, /[----]/ """,
         ['REGEX /????/', 'COMMA ,',
          'REGEX /++++/', 'COMMA ,', 'REGEX /[----]/']
         ),

    ), (
        'regex_stress_test_1',
        # Stress cases from
        # http://stackoverflow.com/questions/5533925/
        # what-javascript-constructs-does-jslex-incorrectly-lex/5573409#5573409
        (r"""/\[/""", [r"""REGEX /\[/"""]),
    ), (
        'regex_stress_test_2',
        (r"""/[i]/""", [r"""REGEX /[i]/"""]),
    ), (
        'regex_stress_test_3',
        (r"""/[\]]/""", [r"""REGEX /[\]]/"""]),
    ), (
        'regex_stress_test_4',
        (r"""/a[\]]/""", [r"""REGEX /a[\]]/"""]),
    ), (
        'regex_stress_test_5',
        (r"""/a[\]]b/""", [r"""REGEX /a[\]]b/"""]),
    ), (
        'regex_stress_test_6',
        (r"""/[\]/]/gi""", [r"""REGEX /[\]/]/gi"""]),
    ), (
        'regex_stress_test_7',
        (r"""/\[[^\]]+\]/gi""", [r"""REGEX /\[[^\]]+\]/gi"""]),
    ), (
        'regex_stress_test_8',
        (r"""
         rexl.re = {
         NAME: /^(?!\d)(?:\w)+|^"(?:[^"]|"")+"/,
         UNQUOTED_LITERAL: /^@(?:(?!\d)(?:\w|\:)+|^"(?:[^"]|"")+")\[[^\]]+\]/,
         QUOTED_LITERAL: /^'(?:[^']|'')*'/,
         NUMERIC_LITERAL: /^[0-9]+(?:\.[0-9]*(?:[eE][-+][0-9]+)?)?/,
         SYMBOL: /^(?:==|=|<>|<=|<|>=|>|!~~|!~|~~|~|!==|!=|!~=|!~|!|&|\||\.|\:|,|\(|\)|\[|\]|\{|\}|\?|\:|;|@|\^|\/\+|\/|\*|\+|-)/
         };
         """, [
         "ID rexl", "PERIOD .", "ID re", "EQ =", "LBRACE {",
         "ID NAME", "COLON :",
         r"""REGEX /^(?!\d)(?:\w)+|^"(?:[^"]|"")+"/""", "COMMA ,",
         "ID UNQUOTED_LITERAL", "COLON :",
         r"""REGEX /^@(?:(?!\d)(?:\w|\:)+|^"(?:[^"]|"")+")\[[^\]]+\]/""",
         "COMMA ,", "ID QUOTED_LITERAL", "COLON :",
         r"""REGEX /^'(?:[^']|'')*'/""", "COMMA ,", "ID NUMERIC_LITERAL",
         "COLON :",
         r"""REGEX /^[0-9]+(?:\.[0-9]*(?:[eE][-+][0-9]+)?)?/""", "COMMA ,",
         "ID SYMBOL", "COLON :",
         r"""REGEX /^(?:==|=|<>|<=|<|>=|>|!~~|!~|~~|~|!==|!=|!~=|!~|!|&|\||\.|\:|,|\(|\)|\[|\]|\{|\}|\?|\:|;|@|\^|\/\+|\/|\*|\+|-)/""",
         "RBRACE }", "SEMI ;"]),
    ), (
        'regex_stress_test_9',
        (r"""
         rexl.re = {
         NAME: /^(?!\d)(?:\w)+|^"(?:[^"]|"")+"/,
         UNQUOTED_LITERAL: /^@(?:(?!\d)(?:\w|\:)+|^"(?:[^"]|"")+")\[[^\]]+\]/,
         QUOTED_LITERAL: /^'(?:[^']|'')*'/,
         NUMERIC_LITERAL: /^[0-9]+(?:\.[0-9]*(?:[eE][-+][0-9]+)?)?/,
         SYMBOL: /^(?:==|=|<>|<=|<|>=|>|!~~|!~|~~|~|!==|!=|!~=|!~|!|&|\||\.|\:|,|\(|\)|\[|\]|\{|\}|\?|\:|;|@|\^|\/\+|\/|\*|\+|-)/
         };
         str = '"';
         """, [
         "ID rexl", "PERIOD .", "ID re", "EQ =", "LBRACE {",
         "ID NAME", "COLON :", r"""REGEX /^(?!\d)(?:\w)+|^"(?:[^"]|"")+"/""",
         "COMMA ,", "ID UNQUOTED_LITERAL", "COLON :",
         r"""REGEX /^@(?:(?!\d)(?:\w|\:)+|^"(?:[^"]|"")+")\[[^\]]+\]/""",
         "COMMA ,", "ID QUOTED_LITERAL", "COLON :",
         r"""REGEX /^'(?:[^']|'')*'/""", "COMMA ,",
         "ID NUMERIC_LITERAL", "COLON :",
         r"""REGEX /^[0-9]+(?:\.[0-9]*(?:[eE][-+][0-9]+)?)?/""", "COMMA ,",
         "ID SYMBOL", "COLON :",
         r"""REGEX /^(?:==|=|<>|<=|<|>=|>|!~~|!~|~~|~|!==|!=|!~=|!~|!|&|\||\.|\:|,|\(|\)|\[|\]|\{|\}|\?|\:|;|@|\^|\/\+|\/|\*|\+|-)/""",
         "RBRACE }", "SEMI ;",
         "ID str", "EQ =", """STRING '"'""", "SEMI ;",
         ]),
    ), (
        'regex_stress_test_10',
        (r""" this._js = "e.str(\"" + this.value.replace(/\\/g, "\\\\").replace(/"/g, "\\\"") + "\")"; """,
         ["THIS this", "PERIOD .", "ID _js", "EQ =",
          r'''STRING "e.str(\""''', "PLUS +", "THIS this", "PERIOD .",
          "ID value", "PERIOD .", "ID replace", "LPAREN (", r"REGEX /\\/g",
          "COMMA ,", r'STRING "\\\\"', "RPAREN )", "PERIOD .", "ID replace",
          "LPAREN (", r'REGEX /"/g', "COMMA ,", r'STRING "\\\""', "RPAREN )",
          "PLUS +", r'STRING "\")"', "SEMI ;"]),
    ), (
        'regex_division_check',
        ('a = /a/ / /b/',
         ['ID a', 'EQ =', 'REGEX /a/', 'DIV /', 'REGEX /b/']),
    ), (
        'regex_after_plus_brace',
        ('+{}/a/g',
         ['PLUS +', 'LBRACE {', 'RBRACE }', 'DIV /', 'ID a', 'DIV /', 'ID g']),
        # The following pathological cases cannot be tested using the
        # lexer alone, as the rules can only be addressed in conjunction
        # with a parser
        #
        # 'regex_after_brace',
        # ('{}/a/g',
        #  ['LBRACE {', 'RBRACE }', 'REGEX /a/g']),
        # 'regex_after_if_brace',
        # ('if (a) { } /a/.test(a)',
        #  ['IF if', 'LPAREN (', 'ID a', 'RPAREN )', 'LBRACE {', 'RBRACE }',
        #   'REGEX /a/', "PERIOD .", "ID test", 'LPAREN (', 'ID a',
        #   'RPAREN )']),
    ), (
        'regex_case',
        ('switch(0){case /a/:}',
         ['SWITCH switch', 'LPAREN (', 'NUMBER 0', 'RPAREN )', 'LBRACE {',
          'CASE case', 'REGEX /a/', 'COLON :', 'RBRACE }']),
    ), (
        'div_after_valid_statement_function_call',
        ('if(){} f(a) / f(b)',
         ['IF if', 'LPAREN (', 'RPAREN )', 'LBRACE {', 'RBRACE }',
          'ID f', 'LPAREN (', 'ID a', 'RPAREN )', 'DIV /',
          'ID f', 'LPAREN (', 'ID b', 'RPAREN )']),
    ), (
        'for_regex_slimit_issue_54',
        ('for (;;) /r/;',
         ['FOR for', 'LPAREN (', 'SEMI ;', 'SEMI ;', 'RPAREN )',
          'REGEX /r/', 'SEMI ;']),
    ), (
        'for_regex_slimit_issue_54_not_break_division',
        ('for (;;) { x / y }',
         ['FOR for', 'LPAREN (', 'SEMI ;', 'SEMI ;', 'RPAREN )',
          'LBRACE {', 'ID x', 'DIV /', 'ID y', 'RBRACE }']),
    ), (
        'for_regex_slimit_issue_54_bracket_accessor_check',
        ('s = {a:1} + s[2] / 1',
         ['ID s', 'EQ =', 'LBRACE {', 'ID a', 'COLON :', 'NUMBER 1',
          'RBRACE }', 'PLUS +', 'ID s', 'LBRACKET [', 'NUMBER 2', 'RBRACKET ]',
          'DIV /', 'NUMBER 1'])
    ), (
        'for_regex_slimit_issue_54_function_parentheses_check',
        ('s = {a:1} + f(2) / 1',
         ['ID s', 'EQ =', 'LBRACE {', 'ID a', 'COLON :', 'NUMBER 1',
          'RBRACE }', 'PLUS +', 'ID f', 'LPAREN (', 'NUMBER 2', 'RPAREN )',
          'DIV /', 'NUMBER 1'])
    ), (
        'for_regex_slimit_issue_54_math_parentheses_check',
        ('s = {a:1} + (2) / 1',
         ['ID s', 'EQ =', 'LBRACE {', 'ID a', 'COLON :', 'NUMBER 1',
          'RBRACE }', 'PLUS +', 'LPAREN (', 'NUMBER 2', 'RPAREN )',
          'DIV /', 'NUMBER 1'])
    ), (
        'for_regex_slimit_issue_54_math_bracket_check',
        ('s = {a:1} + [2] / 1',
         ['ID s', 'EQ =', 'LBRACE {', 'ID a', 'COLON :', 'NUMBER 1',
          'RBRACE }', 'PLUS +', 'LBRACKET [', 'NUMBER 2', 'RBRACKET ]',
          'DIV /', 'NUMBER 1'])
    ), (
        'for_regex_slimit_issue_54_math_braces_check',
        ('s = {a:2} / 166 / 9',
         ['ID s', 'EQ =', 'LBRACE {', 'ID a', 'COLON :', 'NUMBER 2',
          'RBRACE }', 'DIV /', 'NUMBER 166', 'DIV /', 'NUMBER 9'])
    ), (
        'do_while_regex',
        ('do {} while (0) /s/',
         ['DO do', 'LBRACE {', 'RBRACE }', 'WHILE while', 'LPAREN (',
          'NUMBER 0', 'RPAREN )', 'REGEX /s/'])
    ), (
        'if_regex',
        ('if (thing) /s/',
         ['IF if', 'LPAREN (', 'ID thing', 'RPAREN )', 'REGEX /s/'])
    ), (
        'identifier_math',
        ('f (v) /s/g',
         ['ID f', 'LPAREN (', 'ID v', 'RPAREN )', 'DIV /', 'ID s', 'DIV /',
          'ID g'])
    ), (
        'section_7',
        ("a = b\n/hi/s",
         ['ID a', 'EQ =', 'ID b', 'DIV /', 'ID hi', 'DIV /', 'ID s'])
    ), (
        'section_7_extras',
        ("a = b\n\n\n/hi/s",
         ['ID a', 'EQ =', 'ID b', 'DIV /', 'ID hi', 'DIV /', 'ID s'])
    ), (
        'slimit_issue_39_and_57',
        (r"f(a, 'hi\01').split('\1').split('\0');",
         ['ID f', 'LPAREN (', 'ID a', 'COMMA ,', r"STRING 'hi\01'", 'RPAREN )',
          'PERIOD .', 'ID split', 'LPAREN (', r"STRING '\1'", 'RPAREN )',
          'PERIOD .', 'ID split', 'LPAREN (', r"STRING '\0'", 'RPAREN )',
          'SEMI ;'])
    ), (
        'section_7_8_4_string_literal_with_7_3_conformance',
        ("'<LF>\\\n<CR>\\\r<LS>\\\u2028<PS>\\\u2029<CR><LF>\\\r\n'",
         ["STRING '<LF>\\\n<CR>\\\r<LS>\\\u2028<PS>\\\u2029<CR><LF>\\\r\n'"])
    ), (
        # okay this is getting ridiculous how bad ECMA is.
        'section_7_comments',
        ("a = b\n/** **/\n\n/hi/s",
         ['ID a', 'EQ =', 'ID b', 'DIV /', 'ID hi', 'DIV /', 'ID s'])
    ),
]

# various string related syntax errors
es5_error_cases_str = [
    (
        'unterminated_string_eof',
        "var foo = 'test",
        'Unterminated string literal "\'test" at 1:11',
    ), (
        'naked_line_separator_in_string',
        "vaf foo = 'test\u2028foo'",
        'Unterminated string literal "\'test" at 1:11',
    ), (
        'naked_line_feed_in_string',
        "var foo = 'test\u2029foo'",
        'Unterminated string literal "\'test" at 1:11',
    ), (
        'naked_crnl_in_string',
        "var foo = 'test\r\nfoo'",
        'Unterminated string literal "\'test" at 1:11',
    ), (
        'naked_cr_in_string',
        "var foo = 'test\\\n\rfoo'",
        # FIXME Note that the \\ is double escaped
        'Unterminated string literal "\'test\\\\" at 1:11',
    ), (
        'invalid_hex_sequence',
        "var foo = 'fail\\x1'",
        # backticks are converted to single quotes
        "Invalid hexadecimal escape sequence `\\x1` at 1:16",
    ), (
        'invalid_unicode_sequence',
        "var foo = 'fail\\u12'",
        "Invalid unicode escape sequence `\\u12` at 1:16",
    ), (
        'invalid_hex_sequence_multiline',
        "var foo = 'foobar\\\r\nfail\\x1'",
        # backticks are converted to single quotes
        "Invalid hexadecimal escape sequence `\\x1` at 2:5",
    ), (
        'invalid_unicode_sequence_multiline',
        "var foo = 'foobar\\\nfail\\u12'",
        "Invalid unicode escape sequence `\\u12` at 2:5",
    ), (
        'long_invalid_string_truncated',
        "var foo = '1234567890abcdetruncated",
        'Unterminated string literal "\'1234567890abcde..." at 1:11',
    )
]

es5_comment_cases = [
    (
        'line_comment_whole',
        ('//comment\na = 5;\n',
         ['LINE_COMMENT //comment', 'ID a', 'EQ =', 'NUMBER 5', 'SEMI ;']),
    ), (
        'line_comment_trail',
        ('a//comment', ['ID a', 'LINE_COMMENT //comment']),
    ), (
        'block_comment_single',
        ('/***/b/=3//line',
         ['BLOCK_COMMENT /***/', 'ID b', 'DIVEQUAL /=',
          'NUMBER 3', 'LINE_COMMENT //line']),
    ), (
        'block_comment_multiline',
        ('/*\n * Copyright LGPL 2011 \n*/\na = 1;',
         ['BLOCK_COMMENT /*\n * Copyright LGPL 2011 \n*/',
          'ID a', 'EQ =', 'NUMBER 1', 'SEMI ;']),
    ), (
        # this will replace the standard test cases
        'section_7_comments',
        ("a = b\n/** **/\n\n/hi/s",
         ['ID a', 'EQ =', 'ID b', 'BLOCK_COMMENT /** **/', 'DIV /', 'ID hi',
          'DIV /', 'ID s'])
    )
]

# replace the section_7_comments test case
es5_all_cases = es5_cases[:-1] + es5_comment_cases

# double quote version
es5_error_cases_str_dq = [
    (n, arg.translate(swapquotes), msg.translate(swapquotes))
    for n, arg, msg in es5_error_cases_str
]

# single quote version
es5_error_cases_str_sq = [
    (n, arg, msg.translate({96: 39}))
    for n, arg, msg in es5_error_cases_str
]

es5_pos_cases = [
    (
        'single_line',
        """
        var foo = bar;  // line 1
        """, ([
            'var 1:0', 'foo 1:4', '= 1:8', 'bar 1:10', '; 1:13'
        ], [
            'var 1:1', 'foo 1:5', '= 1:9', 'bar 1:11', '; 1:14',
        ])
    ), (
        'multi_line',
        """
        var foo = bar;  // line 1


        var bar = baz;  // line 4
        """, ([
            'var 1:0', 'foo 1:4', '= 1:8', 'bar 1:10', '; 1:13',
            'var 4:28', 'bar 4:32', '= 4:36', 'baz 4:38', '; 4:41',
        ], [
            'var 1:1', 'foo 1:5', '= 1:9', 'bar 1:11', '; 1:14',
            'var 4:1', 'bar 4:5', '= 4:9', 'baz 4:11', '; 4:14',
        ])
    ), (
        'inline_comment',
        """
        // this is a comment  // line 1
        var foo = bar;  // line 2

        // another one  // line 4
        var bar = baz;  // line 5
        """, ([
            'var 2:32', 'foo 2:36', '= 2:40', 'bar 2:42', '; 2:45',
            'var 5:85', 'bar 5:89', '= 5:93', 'baz 5:95', '; 5:98',
        ], [
            'var 2:1', 'foo 2:5', '= 2:9', 'bar 2:11', '; 2:14',
            'var 5:1', 'bar 5:5', '= 5:9', 'baz 5:11', '; 5:14',
        ])
    ), (
        'block_comment',
        """
        /*
        This is a block comment
        */
        var foo = bar;  // line 4

        /* block single line */ // line 6
        var bar = baz;  // line 7

        /* oops */bar();  // line 9

          foo();
        """, ([
            'var 4:30', 'foo 4:34', '= 4:38', 'bar 4:40', '; 4:43',
            'var 7:91', 'bar 7:95', '= 7:99', 'baz 7:101', '; 7:104',
            'bar 9:128', '( 9:131', ') 9:132', '; 9:133',
            'foo 11:149', '( 11:152', ') 11:153', '; 11:154',
        ], [
            'var 4:1', 'foo 4:5', '= 4:9', 'bar 4:11', '; 4:14',
            'var 7:1', 'bar 7:5', '= 7:9', 'baz 7:11', '; 7:14',
            'bar 9:11', '( 9:14', ') 9:15', '; 9:16',
            'foo 11:3', '( 11:6', ') 11:7', '; 11:8',
        ])
    ), (
        'syntax_error_heading_comma',
        """
        var a;
        , b;
        """, ([
            'var 1:0', 'a 1:4', '; 1:5',
            ', 2:7', 'b 2:9', '; 2:10'
        ], [
            'var 1:1', 'a 1:5', '; 1:6',
            ', 2:1', 'b 2:3', '; 2:4'
        ])
    )
]


def run_lexer(value, lexer_cls):
    lexer = lexer_cls()
    lexer.input(value)
    return ['%s %s' % (token.type, token.value) for token in lexer]


def run_lexer_pos(value, lexer_cls):
    lexer = lexer_cls()
    lexer.input(textwrap.dedent(value).strip())
    tokens = list(lexer)
    return ([
        '%s %d:%d' % (token.value, token.lineno, token.lexpos)
        for token in tokens
    ], [
        '%s %d:%d' % (token.value, token.lineno, token.colno)
        for token in tokens
    ])
