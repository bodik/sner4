# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsing simple boolean enabled filter expressions into sqlalchemy-filters tree
"""

import json
from lark import Lark, Transformer


# Boolean expression definition widely recognizes basic building blocks as
# 'terms' and 'factors', do not confuse them with parser's terminals. Also note
# that EBNF expresses logic operators precedence.
#
# https://unnikked.ga/how-to-build-a-boolean-expression-evaluator-518e9e068a65
# https://cs.stackexchange.com/questions/10558/grammar-for-describing-boolean-expressions-with-and-or-and-not/10622#10622
SEARCH_GRAMMAR = r"""
    ?start: expression

    expression: term ("OR" term)*
    term: _factor ("AND" _factor)*
    _factor: criteria | "(" expression ")"

    criteria: COLSPEC OP _value
    COLSPEC: /[a-z]+\.[a-z]+/i
    OP: "==" | "!=" | ">" | "<" | ">=" | "<=" | "ilike" | "not_ilike" | "is_null" | "is_not_null" | "in" | "not_in" | "any" | "not_all"

    _value: _item | array
    _item: string | number
    array: "[" [_item ("," _item)*] "]"
    string: ESCAPED_STRING
    number: SIGNED_NUMBER

    %import common.ESCAPED_STRING
    %import common.SIGNED_NUMBER
    %import common.WS
    %ignore WS
"""


class TreeToSAFilter(Transformer):
    """grammar tree to filters transformer"""

    def expression(self, args):  # pylint: disable=no-self-use
        """transform disjunction"""
        return {'or': args} if len(args) > 1 else args[0]

    def term(self, args):  # pylint: disable=no-self-use
        """transform conjunction"""
        return {'and': args} if len(args) > 1 else args[0]

    def criteria(self, args):  # pylint: disable=no-self-use
        """transform criteria"""
        return dict(zip(['model', 'field', 'op', 'value'], args[0].value.split('.')+[args[1].value, args[2]]))

    def array(self, args):  # pylint: disable=no-self-use
        """transform array; return plain list, discarding the object"""
        return args

    def string(self, args):  # pylint: disable=no-self-use
        """unquote string"""
        return json.loads(args[0])

    def number(self, args):  # pylint: disable=no-self-use
        """cast to actual number type"""
        return float(args[0])


filter_parser = Lark(SEARCH_GRAMMAR, parser='lalr', lexer='standard', transformer=TreeToSAFilter())  # pylint: disable=invalid-name


def test(testcase, expected):
    """test helper"""

    output = filter_parser.parse(testcase)
    print('testcase: %s outputs %s' % (testcase, output))
    assert output == expected


def test_all():
    """perform all tests"""

    # parsing
    test('A.a=="a\\"]a"', {'model': 'A', 'field': 'a', 'op': '==', 'value': 'a"]a'})
    test('A.a in [1,2]', {'model': 'A', 'field': 'a', 'op': 'in', 'value': [1, 2]})
    test('A.a not_in ["1","]2\\""]', {'model': 'A', 'field': 'a', 'op': 'not_in', 'value': ['1', ']2"']})

    # AND parsing
    test('A.a=="a"', {'model': 'A', 'field': 'a', 'op': '==', 'value': 'a'})
    test(
        'A.a=="a" AND B.b=="b"',
        {'and': [
            {'model': 'A', 'field': 'a', 'op': '==', 'value': 'a'},
            {'model': 'B', 'field': 'b', 'op': '==', 'value': 'b'}
        ]}
    )
    test(
        'A.a=="a" AND B.b=="b" AND C.c=="c"',
        {'and': [
            {'model': 'A', 'field': 'a', 'op': '==', 'value': 'a'},
            {'model': 'B', 'field': 'b', 'op': '==', 'value': 'b'},
            {'model': 'C', 'field': 'c', 'op': '==', 'value': 'c'}
        ]}
    )

    # OR parsing
    test(
        'A.a=="a" OR B.b=="b" OR C.c=="c"',
        {'or': [
            {'model': 'A', 'field': 'a', 'op': '==', 'value': 'a'},
            {'model': 'B', 'field': 'b', 'op': '==', 'value': 'b'},
            {'model': 'C', 'field': 'c', 'op': '==', 'value': 'c'}
        ]}
    )

    # AND precedence
    test(
        'A.a=="a" OR B.b=="b" OR C.c!="c" AND D.d=="d"',
        {'or': [
            {'model': 'A', 'field': 'a', 'op': '==', 'value': 'a'},
            {'model': 'B', 'field': 'b', 'op': '==', 'value': 'b'},
            {'and': [
                {'model': 'C', 'field': 'c', 'op': '!=', 'value': 'c'},
                {'model': 'D', 'field': 'd', 'op': '==', 'value': 'd'}
            ]}
        ]}
    )

    # algebra vs misc values
    test(
        'A.a=="a" AND B.b in [1, 2] OR C.c in ["3]\\""]',
        {'or': [
            {'and': [
                {'model': 'A', 'field': 'a', 'op': '==', 'value': 'a'},
                {'model': 'B', 'field': 'b', 'op': 'in', 'value': [1, 2]}
            ]},
            {'model': 'C', 'field': 'c', 'op': 'in', 'value': ['3]"']}
        ]}
    )
