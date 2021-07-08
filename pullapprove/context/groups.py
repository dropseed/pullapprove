from typing import List

from .base import ContextObject, ContextObjectList


class Group(ContextObject):
    """A PullApprove review group"""

    _eq_attr = "name"
    _contains_attr = "name"


class Groups(ContextObjectList):
    """
    Groups is a list of [Group](#group) objects with a few handy shortcuts.
    """

    _eq_attr = "names"
    _contains_attr = "names"
    _item_type = Group

    @property
    def names(self) -> List[str]:
        return [x.name for x in self._items]  # type: ignore

    @property
    def active(self) -> "Groups":
        return Groups([x for x in self._data if x["is_active"]])

    @property
    def inactive(self) -> "Groups":
        return Groups([x for x in self._data if not x["is_active"]])

    @property
    def passing(self) -> "Groups":
        return Groups([x for x in self._data if x["is_passing"]])

    @property
    def approved(self) -> "Groups":
        """Groups that have the necessary reviews and meet any additional requirements"""
        return Groups([x for x in self._data if x["state"] == "approved"])

    @property
    def pending(self) -> "Groups":
        return Groups([x for x in self._data if x["state"] == "pending"])

    @property
    def rejected(self) -> "Groups":
        return Groups([x for x in self._data if x["state"] == "rejected"])

    @property
    def optional(self) -> "Groups":
        return Groups([x for x in self._data if x["type"] == "optional"])

    @property
    def required(self) -> "Groups":
        return Groups([x for x in self._data if x["type"] == "required"])

    @property
    def users_approved(self) -> List[str]:
        users = set()
        for x in self._items:
            users.update(x.users_approved)
        return list(users)

    @property
    def users_rejected(self) -> List[str]:
        users = set()
        for x in self._items:
            users.update(x.users_rejected)
        return list(users)

    @property
    def users_pending(self) -> List[str]:
        users = set()
        for x in self._items:
            users.update(x.users_pending)
        return list(users)

    @property
    def users_unavailable(self) -> List[str]:
        users = set()
        for x in self._items:
            users.update(x.users_unavailable)
        return list(users)

    @property
    def users_available(self) -> List[str]:
        users = set()
        for x in self._items:
            users.update(x.users_available)
        return list(users)
