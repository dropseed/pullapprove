import pytest

from pullapprove.context.base import ContextObject, ContextObjectList


def test_contains_functions(testdata_objs):
    class Item(ContextObject):
        _eq_attr = "name"

    class Items(ContextObjectList):
        _item_type = Item

    items = Items(
        [
            {"name": "One"},
            {"name": "Two"},
        ]
    )

    assert items.get("One").name == "One"
    assert items.get("Two").name == "Two"
    with pytest.raises(KeyError) as e:
        assert items.get("Three").name == "Three"
    assert str(e.value) == "'Found 0 Items with name matching Three'"
