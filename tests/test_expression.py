import re

import pytest

from pullapprove.user_input.expressions import Expression, ExpressionException

context = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "foo": True,
    "bar": True,
    "baz": False,
    "author": "paul",
    "array": [0, 1],
    "farray": [0, 0],
    "tarray": [1, 1],
    "all": all,
    "any": any,
    "search": re.search,
}


def test_list_comprehension_not_supported():
    t = "any([x for x in array])"
    with pytest.raises(ExpressionException) as e:
        Expression(t, context).compile()
    assert "expected token ',', got 'for'" in str(e.value)


def test_search_and_all():
    t = 'search("pa", author) and all(tarray)'
    res = True
    result = Expression(t, context).compile()
    assert res == result


def test_search_function1():
    t = 'search("pa", author)'
    result = Expression(t, context).compile()
    assert result


def test_search_function2():
    t = 'search("pa", "dave")'
    result = Expression(t, context).compile()
    assert result is None


def test_any_function1():
    t = " any ( array ) "
    res = True
    result = Expression(t, context).compile()
    assert result == res


def test_any_function2():
    t = "any(farray)"
    res = False
    result = Expression(t, context).compile()
    assert result == res


def test_all_function1():
    t = "all(tarray)"
    res = True
    result = Expression(t, context).compile()
    assert result == res


def test_all_function2():
    t = "all(array)"
    res = False
    result = Expression(t, context).compile()
    assert result == res


def test_str_2():
    t = "'single quoted'"
    res = "single quoted"
    result = Expression(t, context).compile()
    assert result == res


def test_str_1():
    t = '"double quoted"'
    res = "double quoted"
    result = Expression(t, context).compile()
    assert result == res


def test_paren_6():
    t = "one and (0 or foo)"
    res = True
    result = Expression(t, context).compile()
    assert result == res


def test_and_or():
    t = "one and 0 or foo"
    res = True
    result = Expression(t, context).compile()
    assert result == res


def test_paren_4():
    t = "(one and 1) and baz"
    res = False
    result = Expression(t, context).compile()
    assert result == res


def test_paren_3():
    t = "(one) and (1)"
    res = True
    result = Expression(t, context).compile()
    assert result == res


def test_paren_2():
    t = "((zero and one))"
    res = False
    result = Expression(t, context).compile()
    assert result == res


def test_paren_1():
    t = "(zero and one)"
    res = 0
    result = Expression(t, context).compile()
    assert result == res


def test_paren_simple():
    t = "(zero)"
    res = 0
    result = Expression(t, context).compile()
    assert result == res


def test_double_and1():
    t = "foo and bar and foo"
    res = True
    result = Expression(t, context).compile()
    assert result == res


def test_double_and2():
    t = "foo and bar and baz"
    res = False
    result = Expression(t, context).compile()
    assert result == res


def test_not():
    t = "not baz"
    res = True
    result = Expression(t, context).compile()
    assert result == res


def test_in1():
    t = "0 in array"
    res = True
    result = Expression(t, context).compile()
    assert result == res


def test_in2():
    t = "2 in array"
    res = False
    result = Expression(t, context).compile()
    assert result == res


def test_lte_1():
    t = "0.9 <= 0.9"
    res = True
    result = Expression(t, context).compile()
    assert result == res


def test_gte_1():
    t = "0.9 >= 0.9"
    res = True
    result = Expression(t, context).compile()
    assert result == res


def test_gt_1():
    t = "0.9 > 0"
    res = True
    result = Expression(t, context).compile()
    assert result == res


def test_lt_1():
    t = "0.9 < 0"
    res = False
    result = Expression(t, context).compile()
    assert result == res


def test_lt_2():
    t = "0.9 < 1"
    res = True
    result = Expression(t, context).compile()
    assert result == res


def test_ne():
    t = "zero != 1"
    res = True
    result = Expression(t, context).compile()
    assert result == res


def test_eq():
    t = "zero == 0"
    res = True
    result = Expression(t, context).compile()
    assert result == res


def test_id():
    t = "zero"
    res = 0
    result = Expression(t, context).compile()
    assert result == res


def test_baz_or_bar():
    t = "baz or bar"
    res = True

    result = Expression(t, context).compile()
    assert result is res


def test_baz_or_baz():
    t = "baz or baz"
    res = False

    result = Expression(t, context).compile()
    assert result is res


def test_foo_and_bar():
    t = "foo and bar"
    res = True

    result = Expression(t, context).compile()
    assert result is res


def test_int():
    t = "11"
    res = 11

    result = Expression(t, context).compile()
    assert result == res


def test_float1():
    t = "11.0"
    res = 11.0

    result = Expression(t, context).compile()
    assert result == res


# def test_float2():
#     t = '.1'
#     res = 0.1
#
#     result = Expression(t, context).compile()
#     assert(result == res)

#
# def test_object_name_parsing1():
#     class A:
#         def __init__(self):
#             self.b = 'DEADBEEF'
#
#     ctx = {'a': A()}
#
#     parser = AVisitor(ctx=ctx)
#     val = parser._get_ctx_object_attr_from_path(object=None, attr_path='a.b')
#     assert(val == 'DEADBEEF')
#
#
# def test_object_name_parsing_raise_attribute_error():
#     class C:
#         def __init__(self):
#             self.a = A()
#
#     class A:
#         def __init__(self):
#             self.wrong = 'DEADBEEF'
#
#     ctx = {'c': C()}
#
#     parser = AVisitor(ctx=ctx)
#     with pytest.raises(AttributeError):
#         parser._get_ctx_object_attr_from_path(object=None, attr_path='c.a.b')
#
# def test_object_name_parsing2():
#     class C:
#         def __init__(self):
#             self.a = A()
#
#     class A:
#         def __init__(self):
#             self.b = 'DEADBEEF'
#
#     ctx = {'c': C()}
#
#     parser = AVisitor(ctx=ctx)
#     val = parser._get_ctx_object_attr_from_path(object=None, attr_path='c.a.b')
#     assert(val == 'DEADBEEF')
#


class Commit:
    def __init__(self):
        self.author = "Paul Ortman"
        self.files = ["File1,py", "README.md", "requirements.txt"]


fake_context = {"commit": Commit(), "other": True}


def test_kinda_real_1():
    t = '(commit.author == "Dave") or ("README.md" in commit.files)'
    res = True

    result = Expression(t, fake_context).compile()
    assert result == res


def test_kinda_real_2():
    t = 'commit.author == "Paul Ortman" and "README.md" in commit.files'
    res = True

    result = Expression(t, fake_context).compile()

    assert result == res


# Todo: test operator precedence
