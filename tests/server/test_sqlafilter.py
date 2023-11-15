# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
run sqlafilter parser tests
"""

from sner.server.sqlafilter import FILTER_PARSER


def check(testcase, expected):
    """test helper"""

    output = FILTER_PARSER.parse(testcase)
    print(f'testcase: {testcase} outputs {output}')
    assert output == expected


def test_sqlafilter():
    """perform all tests"""

    # parsing
    check('A.a<"a"', {'model': 'A', 'field': 'a', 'op': '<', 'value': 'a'})
    check('A.a>"a"', {'model': 'A', 'field': 'a', 'op': '>', 'value': 'a'})
    check('A.a<="a"', {'model': 'A', 'field': 'a', 'op': '<=', 'value': 'a'})
    check('A.a>="a"', {'model': 'A', 'field': 'a', 'op': '>=', 'value': 'a'})
    check('A.a=="a\\"]a"', {'model': 'A', 'field': 'a', 'op': '==', 'value': 'a"]a'})
    check('A.a in [1,2]', {'model': 'A', 'field': 'a', 'op': 'in', 'value': [1, 2]})
    check('A.a not_in ["1","]2\\""]', {'model': 'A', 'field': 'a', 'op': 'not_in', 'value': ['1', ']2"']})
    check('A.a astext_not_ilike "dummy%"', {'model': 'A', 'field': 'a', 'op': 'astext_not_ilike', 'value': 'dummy%'})
    check('A.a inet_in "127.0.0.1/32"', {'model': 'A', 'field': 'a', 'op': 'inet_in', 'value': '127.0.0.1/32'})

    # AND parsing
    check('A.a=="a"', {'model': 'A', 'field': 'a', 'op': '==', 'value': 'a'})
    check(
        'A.a=="a" AND B.b=="b"',
        {'and': [
            {'model': 'A', 'field': 'a', 'op': '==', 'value': 'a'},
            {'model': 'B', 'field': 'b', 'op': '==', 'value': 'b'}
        ]}
    )
    check(
        'A.a=="a" AND B.b=="b" AND C.c=="c"',
        {'and': [
            {'model': 'A', 'field': 'a', 'op': '==', 'value': 'a'},
            {'model': 'B', 'field': 'b', 'op': '==', 'value': 'b'},
            {'model': 'C', 'field': 'c', 'op': '==', 'value': 'c'}
        ]}
    )

    # OR parsing
    check(
        'A.a=="a" OR B.b=="b" OR C.c=="c"',
        {'or': [
            {'model': 'A', 'field': 'a', 'op': '==', 'value': 'a'},
            {'model': 'B', 'field': 'b', 'op': '==', 'value': 'b'},
            {'model': 'C', 'field': 'c', 'op': '==', 'value': 'c'}
        ]}
    )

    # AND precedence
    check(
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
    check(
        'A.a=="a" AND B.b in [1, 2] OR C.c in ["3]\\""]',
        {'or': [
            {'and': [
                {'model': 'A', 'field': 'a', 'op': '==', 'value': 'a'},
                {'model': 'B', 'field': 'b', 'op': 'in', 'value': [1, 2]}
            ]},
            {'model': 'C', 'field': 'c', 'op': 'in', 'value': ['3]"']}
        ]}
    )
