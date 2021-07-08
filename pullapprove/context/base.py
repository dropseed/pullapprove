from typing import Any, Callable, Dict, List, Optional

from cached_property import cached_property

from .functions import _contains


class ContextObject:
    """Automatically adds accessors for dict keys"""

    _eq_attr = ""
    _contains_attr = ""
    _subtypes: Dict[str, Any] = {}

    def __init__(self, data: Any) -> None:
        if not hasattr(self, "_eq_attr"):
            raise AttributeError("eq_attr must be set")

        if not hasattr(self, "_contains_attr"):
            raise AttributeError("eq_attr must be set")

        self._data = data
        self._children: Dict[str, ContextObject] = {}
        for key, key_class in self._subtypes.items():
            if self._data.get(key, None):
                self._children[key] = key_class(self._data[key])

        if isinstance(self._data, dict):
            self.__dict__.update(self._data)
        self.__dict__.update(self._children)

    def __str__(self) -> str:
        return str(getattr(self, self._eq_attr))

    def __repr__(self) -> str:
        attr = getattr(self, "_eq_attr")
        return f"<{self.__class__}: {attr}>"

    def __len__(self) -> int:
        return len(self._data)

    def __eq__(self, other) -> bool:
        if isinstance(other, str):
            # if comparing with a string, check specific attr instead
            return other.lower().strip() == getattr(self, self._eq_attr).lower().strip()

        return super().__eq__(other)

    def __contains__(self, key) -> bool:
        return _contains(getattr(self, self._contains_attr), key)


class ContextObjectList(ContextObject):

    _item_type = ContextObject

    def __init__(self, data: List[Any]) -> None:
        super().__init__(data)

        if not hasattr(self, "_item_type"):
            raise AttributeError("item_type must be set")

        assert isinstance(data, list), "data must be a list"

        self._fetch_remote_data: Optional[Callable] = None

    @cached_property
    # TODO fix how functions.py uses this attribute as a type check
    def _items(self):
        if self._fetch_remote_data:
            self._data = self._fetch_remote_data()  # NOQA
        return [self._item_type(x) for x in self._data]

    def __str__(self) -> str:
        strs = [str(item) for item in self._items]
        return ", ".join(strs)

    def __getitem__(self, key):
        return self._items[key]

    def __iter__(self):
        return iter(self._items)

    def get(self, key):
        """
        Gets a specific item in the list using the primary attribute (i.e. name, number, username).
        """
        matches = [x for x in self if x == key]  # uses custom __eq__ in ContextObject
        if len(matches) != 1:
            raise KeyError(
                f"Found {len(matches)} {self.__class__.__name__} with {self._item_type._eq_attr} matching {key}"
            )
        return matches[0]

    def include(self, f):
        """
        Filter down the list of objects using `contains` behavior. Chainable with `exclude`.

        `files.include("src/*")`

        `files.include("src/*").exclude("*.md")`
        """
        return self.__class__([x._data for x in self._items if _contains(x, f)])

    def exclude(self, f):
        """
        Filter down the list of objects using _not_ `contains` behavior. Chainable with `include`.

        `files.exclude("*.md")`

        `files.include("src/*").exclude("*.md")`
        """
        return self.__class__([x._data for x in self._items if not _contains(x, f)])
