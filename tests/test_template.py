import pytest

from pullapprove.user_input.template import TemplateException, render


def test_no_variable():
    template = "Works as is"
    result = render(template=template)

    assert result == "Works as is"


def test_variable():
    template = "{{ test }} is ok"
    result = render(template=template, context={"test": "Good"})

    assert result == "Good is ok"


def test_child_variable():
    template = "{{ test.child }} is better"
    result = render(template=template, context={"test": {"child": "Sweet"}})

    assert result == "Sweet is better"


def test_unkown_variable():
    template = "{{ test }} is ok"
    with pytest.raises(TemplateException) as e:
        render(template=template, context={"tester": "Good"})
        # assert e.message == "'test' is undeadsffined"  # these don't get reached...

    template = "{{ test.sub }} is ok"
    with pytest.raises(TemplateException) as e:
        render(template=template, context={"test": {"another": True}})
        # assert e.message == "'test' is undasdfefined"  # these don't get reached...


def test_extends():
    template = "{% extends 'test.html' %} uh oh"
    with pytest.raises(TemplateException) as e:
        render(template=template)
        # assert e.messsage == 'Extending templateasdfs is not allowed'  # these don't get reached...


def test_len_func():
    template = "{{ len(test.child) }} is better"
    with pytest.raises(TemplateException) as e:
        render(template=template, context={"test": {"child": "Sweet"}})
        # assert e.message == 'len is unadsfadefined'  # these don't get reached...

    template = "{{ len(test.child) }} is better"
    result = render(template=template, context={"test": {"child": "Sweet"}, "len": len})

    assert result == "5 is better"


# line breaks
# html
