###############################################################################
#
# Copyright (c) 2011 Ruslan Spivak
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
###############################################################################

__author__ = 'Ruslan Spivak <ruslan.spivak@gmail.com>'

from functools import partial

import ply.yacc

from calmjs.parse.exceptions import ECMASyntaxError
from calmjs.parse.exceptions import ProductionError
from calmjs.parse.lexers.tokens import AutoLexToken
from calmjs.parse.lexers.es5 import Lexer
from calmjs.parse.factory import AstTypesFactory
from calmjs.parse.unparsers.es5 import pretty_print
from calmjs.parse.walkers import ReprWalker
from calmjs.parse.utils import generate_tab_names
from calmjs.parse.utils import format_lex_token
from calmjs.parse.utils import str
from calmjs.parse.io import read as io_read

asttypes = AstTypesFactory(pretty_print, ReprWalker())

# The default values for the `Parser` constructor, passed on to ply; they must
# be strings
lextab, yacctab = generate_tab_names(__name__)


class Parser(object):
    """JavaScript parser(ECMA-262 5th edition grammar).

    The '*noin' variants are needed to avoid confusing the `in` operator in
    a relational expression with the `in` operator in a `for` statement.

    '*nobf' stands for 'no brace or function'

    This is a stateful, low level parser.  Please use the parse function
    instead for general, higher level usage.
    """

    def __init__(self, lex_optimize=True, lextab=lextab,
                 yacc_optimize=True, yacctab=yacctab, yacc_debug=False,
                 yacc_tracking=True, with_comments=False, asttypes=asttypes):
        # A warning: in order for line numbers and column numbers be
        # tracked correctly, ``yacc_tracking`` MUST be turned ON.  As
        # this parser was initially implemented with a number of manual
        # tracking features that was also added to the lexer,
        # construction of the Node subclasses may require the calling of
        # the `setpos` method with an index to the YaccProduction slice
        # index that contain the tracked token.  The indexes were
        # generally determined with yacc_tracking OFF, through the
        # manual tracking that got added, before turning it back ON for
        # standard usage.

        self.lex_optimize = lex_optimize
        self.lextab = lextab
        self.yacc_optimize = yacc_optimize
        self.yacctab = yacctab
        self.yacc_debug = yacc_debug
        self.yacc_tracking = yacc_tracking

        self.lexer = Lexer(with_comments=with_comments)
        self.lexer.build(optimize=lex_optimize, lextab=lextab)
        self.tokens = self.lexer.tokens

        self.parser = ply.yacc.yacc(
            module=self, optimize=yacc_optimize,
            debug=yacc_debug, tabmodule=yacctab, start='program')

        self.asttypes = asttypes

    def _raise_syntax_error(self, token):
        tokens = [format_lex_token(t) for t in [
            self.lexer.valid_prev_token,
            None if isinstance(token, AutoLexToken) else token,
            self.lexer.token()
        ] if t is not None]
        msg = (
            'Unexpected end of input',
            'Unexpected end of input after {0}',
            'Unexpected {1} after {0}',
            'Unexpected {1} between {0} and {2}',
        )
        raise ECMASyntaxError(msg[len(tokens)].format(*tokens))

    def parse(self, text, debug=False):
        if not isinstance(text, str):
            raise TypeError("'%s' argument expected, got '%s'" % (
                str.__name__, type(text).__name__))

        try:
            return self.parser.parse(
                text, lexer=self.lexer, debug=debug,
                tracking=self.yacc_tracking)
        except ProductionError as e:
            raise e.args[0]

    def p_empty(self, p):
        """empty :"""

    def p_error(self, token):
        next_token = self.lexer.auto_semi(token)
        if next_token is not None:
            self.parser.errok()
            return next_token
        # try to use the token in the actual lexer over the token that
        # got passed in.
        cur_token = self.lexer.cur_token or token
        if (cur_token.type == 'DIV' and self.lexer.valid_prev_token.type in (
                'RBRACE', 'PLUSPLUS', 'MINUSMINUS')):
            # this is the most pathological case in JavaScript; given
            # the usage of the LRParser there is no way to use the rules
            # below to signal the specific "safe" cases, so we have to
            # wait until such an error to occur for specific tokens and
            # attempt to backtrack here
            regex_token = self.lexer.backtracked_token(pos=1)
            if regex_token.type == 'REGEX':
                self.parser.errok()
                return regex_token
        self._raise_syntax_error(token)

    # Comment rules
    # def p_single_line_comment(self, p):
    #     """single_line_comment : LINE_COMMENT"""
    #     pass

    # def p_multi_line_comment(self, p):
    #     """multi_line_comment : BLOCK_COMMENT"""
    #     pass

    # Main rules

    def p_program(self, p):
        """program : source_elements"""
        p[0] = self.asttypes.ES5Program(p[1])
        p[0].setpos(p)  # require yacc_tracking
        # TODO should consume all remaining comment tokens from lexer,
        # so trailing comments be provided

    def p_source_elements(self, p):
        """source_elements : empty
                           | source_element_list
        """
        p[0] = p[1]

    def p_source_element_list(self, p):
        """source_element_list : source_element
                               | source_element_list source_element
        """
        if len(p) == 2:  # single source element
            p[0] = [p[1]]
        else:
            p[1].append(p[2])
            p[0] = p[1]

    def p_source_element(self, p):
        """source_element : statement
                          | function_declaration
        """
        p[0] = p[1]

    def p_statement(self, p):
        """statement : block
                     | variable_statement
                     | empty_statement
                     | expr_statement
                     | if_statement
                     | iteration_statement
                     | continue_statement
                     | break_statement
                     | return_statement
                     | with_statement
                     | switch_statement
                     | labelled_statement
                     | throw_statement
                     | try_statement
                     | debugger_statement
                     | function_declaration
        """
        p[0] = p[1]

    # By having source_elements in the production we support
    # also function_declaration inside blocks
    def p_block(self, p):
        """block : LBRACE source_elements RBRACE"""
        p[0] = self.asttypes.Block(p[2])
        p[0].setpos(p)

    def p_literal(self, p):
        """literal : null_literal
                   | boolean_literal
                   | numeric_literal
                   | string_literal
                   | regex_literal
        """
        p[0] = p[1]

    def p_boolean_literal(self, p):
        """boolean_literal : TRUE
                           | FALSE
        """
        p[0] = self.asttypes.Boolean(p[1])
        p[0].setpos(p)

    def p_null_literal(self, p):
        """null_literal : NULL"""
        p[0] = self.asttypes.Null(p[1])
        p[0].setpos(p)

    def p_numeric_literal(self, p):
        """numeric_literal : NUMBER"""
        p[0] = self.asttypes.Number(p[1])
        p[0].setpos(p)

    def p_string_literal(self, p):
        """string_literal : STRING"""
        p[0] = self.asttypes.String(p[1])
        p[0].setpos(p)

    def p_regex_literal(self, p):
        """regex_literal : REGEX"""
        p[0] = self.asttypes.Regex(p[1])
        p[0].setpos(p)

    def p_identifier(self, p):
        """identifier : ID"""
        p[0] = self.asttypes.Identifier(p[1])
        p[0].setpos(p)

    # Because reserved words can be used as identifiers under certain
    # conditions...
    def p_reserved_word(self, p):
        """reserved_word : BREAK
                         | CASE
                         | CATCH
                         | CONTINUE
                         | DEBUGGER
                         | DEFAULT
                         | DELETE
                         | DO
                         | ELSE
                         | FINALLY
                         | FOR
                         | FUNCTION
                         | IF
                         | IN
                         | INSTANCEOF
                         | NEW
                         | RETURN
                         | SWITCH
                         | THIS
                         | THROW
                         | TRY
                         | TYPEOF
                         | VAR
                         | VOID
                         | WHILE
                         | WITH
                         | NULL
                         | TRUE
                         | FALSE
                         | CLASS
                         | CONST
                         | ENUM
                         | EXPORT
                         | EXTENDS
                         | IMPORT
                         | SUPER
        """
        p[0] = self.asttypes.Identifier(p[1])
        p[0].setpos(p)

    def p_identifier_name(self, p):
        """identifier_name : identifier
                           | reserved_word
        """
        p[0] = p[1]

    ###########################################
    # Expressions
    ###########################################
    def p_primary_expr(self, p):
        """primary_expr : primary_expr_no_brace
                        | object_literal
        """
        p[0] = p[1]

    def p_primary_expr_no_brace_1(self, p):
        """primary_expr_no_brace : identifier"""
        p[0] = p[1]

    def p_primary_expr_no_brace_2(self, p):
        """primary_expr_no_brace : THIS"""
        p[0] = self.asttypes.This()
        p[0].setpos(p)

    def p_primary_expr_no_brace_3(self, p):
        """primary_expr_no_brace : literal
                                 | array_literal
        """
        p[0] = p[1]

    def p_primary_expr_no_brace_4(self, p):
        """primary_expr_no_brace : LPAREN expr RPAREN"""
        if isinstance(p[2], self.asttypes.GroupingOp):
            # this reduces the grouping operator to one.
            p[0] = p[2]
        else:
            p[0] = self.asttypes.GroupingOp(expr=p[2])
            p[0].setpos(p)

    def p_array_literal_1(self, p):
        """array_literal : LBRACKET elision_opt RBRACKET"""
        p[0] = self.asttypes.Array(items=p[2])
        p[0].setpos(p)

    def p_array_literal_2(self, p):
        """array_literal : LBRACKET element_list RBRACKET
                         | LBRACKET element_list COMMA elision_opt RBRACKET
        """
        items = p[2]
        if len(p) == 6:
            items.extend(p[4])
        p[0] = self.asttypes.Array(items=items)
        p[0].setpos(p)

    def p_element_list(self, p):
        """element_list : elision_opt assignment_expr
                        | element_list COMMA elision_opt assignment_expr
        """
        if len(p) == 3:
            p[0] = p[1] + [p[2]]
        else:
            p[1].extend(p[3])
            p[1].append(p[4])
            p[0] = p[1]

    def p_elision_opt_1(self, p):
        """elision_opt : empty"""
        p[0] = []

    def p_elision_opt_2(self, p):
        """elision_opt : elision"""
        p[0] = p[1]

    def p_elision(self, p):
        """elision : COMMA
                   | elision COMMA
        """
        if len(p) == 2:
            p[0] = [self.asttypes.Elision(1)]
            p[0][0].setpos(p)
        else:
            # increment the Elision value.
            p[1][-1].value += 1
            p[0] = p[1]
        # TODO there should be a cleaner API for the lexer and their
        # token types for ensuring that the mappings are available.
        p[0][0]._token_map = {(',' * p[0][0].value): [
            p[0][0].findpos(p, 0)]}
        return

    def p_object_literal(self, p):
        """object_literal : LBRACE RBRACE
                          | LBRACE property_list RBRACE
                          | LBRACE property_list COMMA RBRACE
        """
        if len(p) == 3:
            p[0] = self.asttypes.Object()
        else:
            p[0] = self.asttypes.Object(properties=p[2])
        p[0].setpos(p)

    def p_property_list(self, p):
        """property_list : property_assignment
                         | property_list COMMA property_assignment
        """
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[1].append(p[3])
            p[0] = p[1]

    # 11.1.5 Object Initialiser
    def p_property_assignment(self, p):
        """property_assignment \
             : property_name COLON assignment_expr
             | GETPROP property_name LPAREN RPAREN LBRACE function_body RBRACE
             | SETPROP property_name LPAREN property_set_parameter_list RPAREN\
                   LBRACE function_body RBRACE
        """
        if len(p) == 4:
            p[0] = self.asttypes.Assign(left=p[1], op=p[2], right=p[3])
            p[0].setpos(p, 2)
        elif len(p) == 8:
            p[0] = self.asttypes.GetPropAssign(prop_name=p[2], elements=p[6])
            p[0].setpos(p)
        else:
            p[0] = self.asttypes.SetPropAssign(
                prop_name=p[2], parameter=p[4], elements=p[7])
            p[0].setpos(p)

    # For the evaluation of Object Initialisere as described in 11.1.5,
    # and property accessors as described in 11.2.1, the IdentifierName
    # is evaluated to a String value, thus they are not to be treated as
    # standard Identifier types.  In this case, it can be marked as a
    # PropIdentifier to identifiy this specific case.
    def p_identifier_name_string(self, p):
        """identifier_name_string : identifier_name
        """
        p[0] = asttypes.PropIdentifier(p[1].value)
        # manually clone the position attributes.
        for k in ('_token_map', 'lexpos', 'lineno', 'colno'):
            setattr(p[0], k, getattr(p[1], k))

    # identifier_name_string ~= identifier_name
    def p_property_name(self, p):
        """property_name : identifier_name_string
                         | string_literal
                         | numeric_literal
        """
        p[0] = p[1]

    def p_property_set_parameter_list(self, p):
        """property_set_parameter_list : identifier
        """
        p[0] = p[1]

    # 11.2 Left-Hand-Side Expressions

    # identifier_name_string ~= identifier_name, as specified in section
    # 11.2.1; same for the further cases.
    def p_member_expr(self, p):
        """member_expr : primary_expr
                       | function_expr
                       | member_expr LBRACKET expr RBRACKET
                       | member_expr PERIOD identifier_name_string
                       | NEW member_expr arguments
        """
        if len(p) == 2:
            p[0] = p[1]
            return

        if p[1] == 'new':
            p[0] = self.asttypes.NewExpr(p[2], p[3])
            p[0].setpos(p)
        elif p[2] == '.':
            p[0] = self.asttypes.DotAccessor(p[1], p[3])
            p[0].setpos(p, 2)
        else:
            p[0] = self.asttypes.BracketAccessor(p[1], p[3])
            p[0].setpos(p, 2)

    def p_member_expr_nobf(self, p):
        """member_expr_nobf : primary_expr_no_brace
                            | function_expr
                            | member_expr_nobf LBRACKET expr RBRACKET
                            | member_expr_nobf PERIOD identifier_name_string
                            | NEW member_expr arguments
        """
        if len(p) == 2:
            p[0] = p[1]
            return

        if p[1] == 'new':
            p[0] = self.asttypes.NewExpr(p[2], p[3])
            p[0].setpos(p, 1)
        elif p[2] == '.':
            p[0] = self.asttypes.DotAccessor(p[1], p[3])
            p[0].setpos(p, 2)
        else:
            p[0] = self.asttypes.BracketAccessor(p[1], p[3])
            p[0].setpos(p, 2)

    def p_new_expr(self, p):
        """new_expr : member_expr
                    | NEW new_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.NewExpr(p[2])
            p[0].setpos(p)

    def p_new_expr_nobf(self, p):
        """new_expr_nobf : member_expr_nobf
                         | NEW new_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.NewExpr(p[2])
            p[0].setpos(p)

    def p_call_expr(self, p):
        """call_expr : member_expr arguments
                     | call_expr arguments
                     | call_expr LBRACKET expr RBRACKET
                     | call_expr PERIOD identifier_name_string
        """
        if len(p) == 3:
            p[0] = self.asttypes.FunctionCall(p[1], p[2])
            p[0].setpos(p)  # require yacc_tracking
        elif len(p) == 4:
            p[0] = self.asttypes.DotAccessor(p[1], p[3])
            p[0].setpos(p, 2)
        else:
            p[0] = self.asttypes.BracketAccessor(p[1], p[3])
            p[0].setpos(p, 2)

    def p_call_expr_nobf(self, p):
        """call_expr_nobf : member_expr_nobf arguments
                          | call_expr_nobf arguments
                          | call_expr_nobf LBRACKET expr RBRACKET
                          | call_expr_nobf PERIOD identifier_name_string
        """
        if len(p) == 3:
            p[0] = self.asttypes.FunctionCall(p[1], p[2])
            p[0].setpos(p)  # require yacc_tracking
        elif len(p) == 4:
            p[0] = self.asttypes.DotAccessor(p[1], p[3])
            p[0].setpos(p, 2)
        else:
            p[0] = self.asttypes.BracketAccessor(p[1], p[3])
            p[0].setpos(p, 2)

    def p_arguments(self, p):
        """arguments : LPAREN RPAREN
                     | LPAREN argument_list RPAREN
        """
        if len(p) == 4:
            p[0] = self.asttypes.Arguments(p[2])
        else:
            p[0] = self.asttypes.Arguments([])
        p[0].setpos(p)

    def p_argument_list(self, p):
        """argument_list : assignment_expr
                         | argument_list COMMA assignment_expr
        """
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[1].append(p[3])
            p[0] = p[1]

    def p_lef_hand_side_expr(self, p):
        """left_hand_side_expr : new_expr
                               | call_expr
        """
        p[0] = p[1]

    def p_lef_hand_side_expr_nobf(self, p):
        """left_hand_side_expr_nobf : new_expr_nobf
                                    | call_expr_nobf
        """
        p[0] = p[1]

    # 11.3 Postfix Expressions
    def p_postfix_expr(self, p):
        """postfix_expr : left_hand_side_expr
                        | left_hand_side_expr PLUSPLUS
                        | left_hand_side_expr MINUSMINUS
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.PostfixExpr(op=p[2], value=p[1])
            p[0].setpos(p, 2)

    def p_postfix_expr_nobf(self, p):
        """postfix_expr_nobf : left_hand_side_expr_nobf
                             | left_hand_side_expr_nobf PLUSPLUS
                             | left_hand_side_expr_nobf MINUSMINUS
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.PostfixExpr(op=p[2], value=p[1])
            p[0].setpos(p, 2)

    # 11.4 Unary Operators
    def p_unary_expr(self, p):
        """unary_expr : postfix_expr
                      | unary_expr_common
        """
        p[0] = p[1]

    def p_unary_expr_nobf(self, p):
        """unary_expr_nobf : postfix_expr_nobf
                           | unary_expr_common
        """
        p[0] = p[1]

    def p_unary_expr_common(self, p):
        """unary_expr_common : DELETE unary_expr
                             | VOID unary_expr
                             | TYPEOF unary_expr
                             | PLUSPLUS unary_expr
                             | MINUSMINUS unary_expr
                             | PLUS unary_expr
                             | MINUS unary_expr
                             | BNOT unary_expr
                             | NOT unary_expr
        """
        p[0] = self.asttypes.UnaryExpr(p[1], p[2])
        p[0].setpos(p)

    # 11.5 Multiplicative Operators
    def p_multiplicative_expr(self, p):
        """multiplicative_expr : unary_expr
                               | multiplicative_expr MULT unary_expr
                               | multiplicative_expr DIV unary_expr
                               | multiplicative_expr MOD unary_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    def p_multiplicative_expr_nobf(self, p):
        """multiplicative_expr_nobf : unary_expr_nobf
                                    | multiplicative_expr_nobf MULT unary_expr
                                    | multiplicative_expr_nobf DIV unary_expr
                                    | multiplicative_expr_nobf MOD unary_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    # 11.6 Additive Operators
    def p_additive_expr(self, p):
        """additive_expr : multiplicative_expr
                         | additive_expr PLUS multiplicative_expr
                         | additive_expr MINUS multiplicative_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    def p_additive_expr_nobf(self, p):
        """additive_expr_nobf : multiplicative_expr_nobf
                              | additive_expr_nobf PLUS multiplicative_expr
                              | additive_expr_nobf MINUS multiplicative_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    # 11.7 Bitwise Shift Operators
    def p_shift_expr(self, p):
        """shift_expr : additive_expr
                      | shift_expr LSHIFT additive_expr
                      | shift_expr RSHIFT additive_expr
                      | shift_expr URSHIFT additive_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    def p_shift_expr_nobf(self, p):
        """shift_expr_nobf : additive_expr_nobf
                           | shift_expr_nobf LSHIFT additive_expr
                           | shift_expr_nobf RSHIFT additive_expr
                           | shift_expr_nobf URSHIFT additive_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    # 11.8 Relational Operators
    def p_relational_expr(self, p):
        """relational_expr : shift_expr
                           | relational_expr LT shift_expr
                           | relational_expr GT shift_expr
                           | relational_expr LE shift_expr
                           | relational_expr GE shift_expr
                           | relational_expr INSTANCEOF shift_expr
                           | relational_expr IN shift_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    def p_relational_expr_noin(self, p):
        """relational_expr_noin : shift_expr
                                | relational_expr_noin LT shift_expr
                                | relational_expr_noin GT shift_expr
                                | relational_expr_noin LE shift_expr
                                | relational_expr_noin GE shift_expr
                                | relational_expr_noin INSTANCEOF shift_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    def p_relational_expr_nobf(self, p):
        """relational_expr_nobf : shift_expr_nobf
                                | relational_expr_nobf LT shift_expr
                                | relational_expr_nobf GT shift_expr
                                | relational_expr_nobf LE shift_expr
                                | relational_expr_nobf GE shift_expr
                                | relational_expr_nobf INSTANCEOF shift_expr
                                | relational_expr_nobf IN shift_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    # 11.9 Equality Operators
    def p_equality_expr(self, p):
        """equality_expr : relational_expr
                         | equality_expr EQEQ relational_expr
                         | equality_expr NE relational_expr
                         | equality_expr STREQ relational_expr
                         | equality_expr STRNEQ relational_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    def p_equality_expr_noin(self, p):
        """equality_expr_noin : relational_expr_noin
                              | equality_expr_noin EQEQ relational_expr
                              | equality_expr_noin NE relational_expr
                              | equality_expr_noin STREQ relational_expr
                              | equality_expr_noin STRNEQ relational_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    def p_equality_expr_nobf(self, p):
        """equality_expr_nobf : relational_expr_nobf
                              | equality_expr_nobf EQEQ relational_expr
                              | equality_expr_nobf NE relational_expr
                              | equality_expr_nobf STREQ relational_expr
                              | equality_expr_nobf STRNEQ relational_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    # 11.10 Binary Bitwise Operators
    def p_bitwise_and_expr(self, p):
        """bitwise_and_expr : equality_expr
                            | bitwise_and_expr BAND equality_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    def p_bitwise_and_expr_noin(self, p):
        """bitwise_and_expr_noin \
            : equality_expr_noin
            | bitwise_and_expr_noin BAND equality_expr_noin
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    def p_bitwise_and_expr_nobf(self, p):
        """bitwise_and_expr_nobf \
            : equality_expr_nobf
            | bitwise_and_expr_nobf BAND equality_expr_nobf
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    def p_bitwise_xor_expr(self, p):
        """bitwise_xor_expr : bitwise_and_expr
                            | bitwise_xor_expr BXOR bitwise_and_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    def p_bitwise_xor_expr_noin(self, p):
        """
        bitwise_xor_expr_noin \
            : bitwise_and_expr_noin
            | bitwise_xor_expr_noin BXOR bitwise_and_expr_noin
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    def p_bitwise_xor_expr_nobf(self, p):
        """
        bitwise_xor_expr_nobf \
            : bitwise_and_expr_nobf
            | bitwise_xor_expr_nobf BXOR bitwise_and_expr_nobf
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    def p_bitwise_or_expr(self, p):
        """bitwise_or_expr : bitwise_xor_expr
                           | bitwise_or_expr BOR bitwise_xor_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    def p_bitwise_or_expr_noin(self, p):
        """
        bitwise_or_expr_noin \
            : bitwise_xor_expr_noin
            | bitwise_or_expr_noin BOR bitwise_xor_expr_noin
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    def p_bitwise_or_expr_nobf(self, p):
        """
        bitwise_or_expr_nobf \
            : bitwise_xor_expr_nobf
            | bitwise_or_expr_nobf BOR bitwise_xor_expr_nobf
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    # 11.11 Binary Logical Operators
    def p_logical_and_expr(self, p):
        """logical_and_expr : bitwise_or_expr
                            | logical_and_expr AND bitwise_or_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    def p_logical_and_expr_noin(self, p):
        """
        logical_and_expr_noin : bitwise_or_expr_noin
                              | logical_and_expr_noin AND bitwise_or_expr_noin
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    def p_logical_and_expr_nobf(self, p):
        """
        logical_and_expr_nobf : bitwise_or_expr_nobf
                              | logical_and_expr_nobf AND bitwise_or_expr_nobf
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    def p_logical_or_expr(self, p):
        """logical_or_expr : logical_and_expr
                           | logical_or_expr OR logical_and_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    def p_logical_or_expr_noin(self, p):
        """logical_or_expr_noin : logical_and_expr_noin
                                | logical_or_expr_noin OR logical_and_expr_noin
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    def p_logical_or_expr_nobf(self, p):
        """logical_or_expr_nobf : logical_and_expr_nobf
                                | logical_or_expr_nobf OR logical_and_expr_nobf
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.BinOp(op=p[2], left=p[1], right=p[3])
            p[0].setpos(p, 2)

    # 11.12 Conditional Operator ( ? : )
    def p_conditional_expr(self, p):
        """
        conditional_expr \
            : logical_or_expr
            | logical_or_expr CONDOP assignment_expr COLON assignment_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.Conditional(
                predicate=p[1], consequent=p[3], alternative=p[5])
            p[0].setpos(p, 2)

    def p_conditional_expr_noin(self, p):
        """
        conditional_expr_noin \
            : logical_or_expr_noin
            | logical_or_expr_noin CONDOP assignment_expr_noin COLON \
                  assignment_expr_noin
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.Conditional(
                predicate=p[1], consequent=p[3], alternative=p[5])
            p[0].setpos(p, 2)

    def p_conditional_expr_nobf(self, p):
        """
        conditional_expr_nobf \
            : logical_or_expr_nobf
            | logical_or_expr_nobf CONDOP assignment_expr COLON assignment_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.Conditional(
                predicate=p[1], consequent=p[3], alternative=p[5])
            p[0].setpos(p, 2)

    # 11.13 Assignment Operators
    def p_assignment_expr(self, p):
        """
        assignment_expr \
            : conditional_expr
            | left_hand_side_expr assignment_operator assignment_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.Assign(left=p[1], op=p[2], right=p[3])
            p[0].setpos(p, 2)  # require yacc_tracking

    def p_assignment_expr_noin(self, p):
        """
        assignment_expr_noin \
            : conditional_expr_noin
            | left_hand_side_expr assignment_operator assignment_expr_noin
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.Assign(left=p[1], op=p[2], right=p[3])
            p[0].setpos(p, 2)  # require yacc_tracking

    def p_assignment_expr_nobf(self, p):
        """
        assignment_expr_nobf \
            : conditional_expr_nobf
            | left_hand_side_expr_nobf assignment_operator assignment_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.Assign(left=p[1], op=p[2], right=p[3])
            p[0].setpos(p, 2)  # require yacc_tracking

    def p_assignment_operator(self, p):
        """assignment_operator : EQ
                               | MULTEQUAL
                               | DIVEQUAL
                               | MODEQUAL
                               | PLUSEQUAL
                               | MINUSEQUAL
                               | LSHIFTEQUAL
                               | RSHIFTEQUAL
                               | URSHIFTEQUAL
                               | ANDEQUAL
                               | XOREQUAL
                               | OREQUAL
        """
        p[0] = p[1]

    # 11.4 Comma Operator
    def p_expr(self, p):
        """expr : assignment_expr
                | expr COMMA assignment_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.Comma(left=p[1], right=p[3])
            p[0].setpos(p, 2)

    def p_expr_noin(self, p):
        """expr_noin : assignment_expr_noin
                     | expr_noin COMMA assignment_expr_noin
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.Comma(left=p[1], right=p[3])
            p[0].setpos(p, 2)

    def p_expr_nobf(self, p):
        """expr_nobf : assignment_expr_nobf
                     | expr_nobf COMMA assignment_expr
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = self.asttypes.Comma(left=p[1], right=p[3])
            p[0].setpos(p, 2)

    # 12.2 Variable Statement
    def p_variable_statement(self, p):
        """variable_statement : VAR variable_declaration_list SEMI
                              | VAR variable_declaration_list AUTOSEMI
        """
        p[0] = self.asttypes.VarStatement(p[2])
        p[0].setpos(p)

    def p_variable_declaration_list(self, p):
        """
        variable_declaration_list \
            : variable_declaration
            | variable_declaration_list COMMA variable_declaration
        """
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[1].append(p[3])
            p[0] = p[1]

    def p_variable_declaration_list_noin(self, p):
        """
        variable_declaration_list_noin \
            : variable_declaration_noin
            | variable_declaration_list_noin COMMA variable_declaration_noin
        """
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[1].append(p[3])
            p[0] = p[1]

    def p_variable_declaration(self, p):
        """variable_declaration : identifier
                                | identifier initializer
        """
        if len(p) == 2:
            p[0] = self.asttypes.VarDecl(p[1])
            p[0].setpos(p)  # require yacc_tracking
        else:
            p[0] = self.asttypes.VarDecl(p[1], p[2])
            p[0].setpos(p, additional=(('=', 2),))  # require yacc_tracking

    def p_variable_declaration_noin(self, p):
        """variable_declaration_noin : identifier
                                     | identifier initializer_noin
        """
        if len(p) == 2:
            p[0] = self.asttypes.VarDecl(p[1])
            p[0].setpos(p)  # require yacc_tracking
        else:
            p[0] = self.asttypes.VarDecl(p[1], p[2])
            p[0].setpos(p, additional=(('=', 2),))  # require yacc_tracking

    def p_initializer(self, p):
        """initializer : EQ assignment_expr"""
        p[0] = p[2]

    def p_initializer_noin(self, p):
        """initializer_noin : EQ assignment_expr_noin"""
        p[0] = p[2]

    # 12.3 Empty Statement
    def p_empty_statement(self, p):
        """empty_statement : SEMI"""
        p[0] = self.asttypes.EmptyStatement(p[1])
        p[0].setpos(p)

    # 12.4 Expression Statement
    def p_expr_statement(self, p):
        """expr_statement : expr_nobf SEMI
                          | expr_nobf AUTOSEMI
        """
        # In 12.4, expression statements cannot start with either the
        # 'function' keyword or '{'.  However, the lexing and production
        # of the FuncExpr nodes can be done through further rules have
        # been done, so flag this as an exception, but must be raised
        # like so due to avoid the SyntaxError being flagged by ply and
        # which would result in an infinite loop in this case.

        if isinstance(p[1], self.asttypes.FuncExpr):
            _, line, col = p[1].getpos('(', 0)
            raise ProductionError(ECMASyntaxError(
                'Function statement requires a name at %s:%s' % (line, col)))

        # The most bare 'block' rule is defined as part of 'statement'
        # and there are no other bare rules that would result in the
        # production of such like for 'function_expr'.

        p[0] = self.asttypes.ExprStatement(p[1])
        p[0].setpos(p)  # require yacc_tracking

    # 12.5 The if Statement
    def p_if_statement_1(self, p):
        """if_statement : IF LPAREN expr RPAREN statement"""
        p[0] = self.asttypes.If(predicate=p[3], consequent=p[5])
        p[0].setpos(p)

    def p_if_statement_2(self, p):
        """if_statement : IF LPAREN expr RPAREN statement ELSE statement"""
        p[0] = self.asttypes.If(
            predicate=p[3], consequent=p[5], alternative=p[7])
        p[0].setpos(p)

    # 12.6 Iteration Statements
    def p_iteration_statement_1(self, p):
        """
        iteration_statement \
            : DO statement WHILE LPAREN expr RPAREN SEMI
            | DO statement WHILE LPAREN expr RPAREN AUTOSEMI
        """
        p[0] = self.asttypes.DoWhile(predicate=p[5], statement=p[2])
        p[0].setpos(p)

    def p_iteration_statement_2(self, p):
        """iteration_statement : WHILE LPAREN expr RPAREN statement"""
        p[0] = self.asttypes.While(predicate=p[3], statement=p[5])
        p[0].setpos(p)

    def p_iteration_statement_3(self, p):
        """
        iteration_statement \
            : FOR LPAREN expr_noin_opt SEMI expr_opt SEMI expr_opt RPAREN \
                  statement
            | FOR LPAREN VAR variable_declaration_list_noin SEMI expr_opt SEMI\
                  expr_opt RPAREN statement
        """
        def wrap(node, key):
            if node is None:
                # work around bug with yacc tracking of empty elements
                # by using the previous token, and increment the
                # positions
                node = self.asttypes.EmptyStatement(';')
                node.setpos(p, key - 1)
                node.lexpos += 1
                node.colno += 1
            else:
                node = self.asttypes.ExprStatement(expr=node)
                node.setpos(p, key)
            return node

        if len(p) == 10:
            p[0] = self.asttypes.For(
                init=wrap(p[3], 3), cond=wrap(p[5], 5),
                count=p[7], statement=p[9])
        else:
            init = self.asttypes.VarStatement(p[4])
            init.setpos(p, 3)
            p[0] = self.asttypes.For(
                init=init, cond=wrap(p[6], 6), count=p[8], statement=p[10])
        p[0].setpos(p)

    def p_iteration_statement_4(self, p):
        """
        iteration_statement \
            : FOR LPAREN left_hand_side_expr IN expr RPAREN statement
        """
        p[0] = self.asttypes.ForIn(item=p[3], iterable=p[5], statement=p[7])
        p[0].setpos(p)

    def p_iteration_statement_5(self, p):
        """
        iteration_statement : \
            FOR LPAREN VAR identifier IN expr RPAREN statement
        """
        vardecl = self.asttypes.VarDeclNoIn(identifier=p[4])
        vardecl.setpos(p, 3)
        p[0] = self.asttypes.ForIn(item=vardecl, iterable=p[6], statement=p[8])
        p[0].setpos(p)

    def p_iteration_statement_6(self, p):
        """
        iteration_statement \
          : FOR LPAREN VAR identifier initializer_noin IN expr RPAREN statement
        """
        vardecl = self.asttypes.VarDeclNoIn(
            identifier=p[4], initializer=p[5])
        vardecl.setpos(p, 3)
        p[0] = self.asttypes.ForIn(item=vardecl, iterable=p[7], statement=p[9])
        p[0].setpos(p)

    def p_expr_opt(self, p):
        """expr_opt : empty
                    | expr
        """
        p[0] = p[1]

    def p_expr_noin_opt(self, p):
        """expr_noin_opt : empty
                         | expr_noin
        """
        p[0] = p[1]

    # 12.7 The continue Statement
    def p_continue_statement_1(self, p):
        """continue_statement : CONTINUE SEMI
                              | CONTINUE AUTOSEMI
        """
        p[0] = self.asttypes.Continue()
        p[0].setpos(p)

    def p_continue_statement_2(self, p):
        """continue_statement : CONTINUE identifier SEMI
                              | CONTINUE identifier AUTOSEMI
        """
        p[0] = self.asttypes.Continue(p[2])
        p[0].setpos(p)

    # 12.8 The break Statement
    def p_break_statement_1(self, p):
        """break_statement : BREAK SEMI
                           | BREAK AUTOSEMI
        """
        p[0] = self.asttypes.Break()
        p[0].setpos(p)

    def p_break_statement_2(self, p):
        """break_statement : BREAK identifier SEMI
                           | BREAK identifier AUTOSEMI
        """
        p[0] = self.asttypes.Break(p[2])
        p[0].setpos(p)

    # 12.9 The return Statement
    def p_return_statement_1(self, p):
        """return_statement : RETURN SEMI
                            | RETURN AUTOSEMI
        """
        p[0] = self.asttypes.Return()
        p[0].setpos(p)

    def p_return_statement_2(self, p):
        """return_statement : RETURN expr SEMI
                            | RETURN expr AUTOSEMI
        """
        p[0] = self.asttypes.Return(expr=p[2])
        p[0].setpos(p)

    # 12.10 The with Statement
    def p_with_statement(self, p):
        """with_statement : WITH LPAREN expr RPAREN statement"""
        p[0] = self.asttypes.With(expr=p[3], statement=p[5])
        p[0].setpos(p)

    # 12.11 The switch Statement
    def p_switch_statement(self, p):
        """switch_statement : SWITCH LPAREN expr RPAREN case_block"""
        # this uses a completely different type that corrects a
        # subtly wrong interpretation of this construct.
        # see: https://github.com/rspivak/slimit/issues/94
        p[0] = self.asttypes.Switch(expr=p[3], case_block=p[5])
        p[0].setpos(p)
        return

    def p_case_block(self, p):
        """
        case_block \
            : LBRACE case_clauses_opt RBRACE
            | LBRACE case_clauses_opt default_clause case_clauses_opt RBRACE
        """
        statements = []
        for s in p[2:-1]:
            if isinstance(s, list):
                for i in s:
                    statements.append(i)
            elif isinstance(s, self.asttypes.Default):
                statements.append(s)
        p[0] = self.asttypes.CaseBlock(statements)
        p[0].setpos(p)

    def p_case_clauses_opt(self, p):
        """case_clauses_opt : empty
                            | case_clauses
        """
        p[0] = p[1]

    def p_case_clauses(self, p):
        """case_clauses : case_clause
                        | case_clauses case_clause
        """
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[1].append(p[2])
            p[0] = p[1]

    def p_case_clause(self, p):
        """case_clause : CASE expr COLON source_elements"""
        p[0] = self.asttypes.Case(expr=p[2], elements=p[4])
        p[0].setpos(p)

    def p_default_clause(self, p):
        """default_clause : DEFAULT COLON source_elements"""
        p[0] = self.asttypes.Default(elements=p[3])
        p[0].setpos(p)

    # 12.12 Labelled Statements
    def p_labelled_statement(self, p):
        """labelled_statement : identifier COLON statement"""
        p[0] = self.asttypes.Label(identifier=p[1], statement=p[3])
        p[0].setpos(p, 2)

    # 12.13 The throw Statement
    def p_throw_statement(self, p):
        """throw_statement : THROW expr SEMI
                           | THROW expr AUTOSEMI
        """
        p[0] = self.asttypes.Throw(expr=p[2])
        p[0].setpos(p)

    # 12.14 The try Statement
    def p_try_statement_1(self, p):
        """try_statement : TRY block catch"""
        p[0] = self.asttypes.Try(statements=p[2], catch=p[3])
        p[0].setpos(p)

    def p_try_statement_2(self, p):
        """try_statement : TRY block finally"""
        p[0] = self.asttypes.Try(statements=p[2], fin=p[3])
        p[0].setpos(p)

    def p_try_statement_3(self, p):
        """try_statement : TRY block catch finally"""
        p[0] = self.asttypes.Try(statements=p[2], catch=p[3], fin=p[4])
        p[0].setpos(p)

    def p_catch(self, p):
        """catch : CATCH LPAREN identifier RPAREN block"""
        p[0] = self.asttypes.Catch(identifier=p[3], elements=p[5])
        p[0].setpos(p)

    def p_finally(self, p):
        """finally : FINALLY block"""
        p[0] = self.asttypes.Finally(elements=p[2])
        p[0].setpos(p)

    # 12.15 The debugger statement
    def p_debugger_statement(self, p):
        """debugger_statement : DEBUGGER SEMI
                              | DEBUGGER AUTOSEMI
        """
        p[0] = self.asttypes.Debugger(p[1])
        p[0].setpos(p)

    # 13 Function Definition
    def p_function_declaration(self, p):
        """
        function_declaration \
            : FUNCTION identifier LPAREN RPAREN LBRACE function_body RBRACE
            | FUNCTION identifier LPAREN formal_parameter_list RPAREN LBRACE \
                 function_body RBRACE
        """
        if len(p) == 8:
            p[0] = self.asttypes.FuncDecl(
                identifier=p[2], parameters=None, elements=p[6])
        else:
            p[0] = self.asttypes.FuncDecl(
                identifier=p[2], parameters=p[4], elements=p[7])
        p[0].setpos(p)

    def p_function_expr_1(self, p):
        """
        function_expr \
            : FUNCTION LPAREN RPAREN LBRACE function_body RBRACE
            | FUNCTION LPAREN formal_parameter_list RPAREN \
                LBRACE function_body RBRACE
        """
        if len(p) == 7:
            p[0] = self.asttypes.FuncExpr(
                identifier=None, parameters=None, elements=p[5])
        else:
            p[0] = self.asttypes.FuncExpr(
                identifier=None, parameters=p[3], elements=p[6])
        p[0].setpos(p)

    def p_function_expr_2(self, p):
        """
        function_expr \
            : FUNCTION identifier LPAREN RPAREN LBRACE function_body RBRACE
            | FUNCTION identifier LPAREN formal_parameter_list RPAREN \
                LBRACE function_body RBRACE
        """
        if len(p) == 8:
            p[0] = self.asttypes.FuncExpr(
                identifier=p[2], parameters=None, elements=p[6])
        else:
            p[0] = self.asttypes.FuncExpr(
                identifier=p[2], parameters=p[4], elements=p[7])
        p[0].setpos(p)

    def p_formal_parameter_list(self, p):
        """formal_parameter_list : identifier
                                 | formal_parameter_list COMMA identifier
        """
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[1].append(p[3])
            p[0] = p[1]

    def p_function_body(self, p):
        """function_body : source_elements"""
        p[0] = p[1]


def parse(source, with_comments=False):
    """
    Return an AST from the input ES5 source.
    """

    parser = Parser(with_comments=with_comments)
    return parser.parse(source)


read = partial(io_read, parse)
