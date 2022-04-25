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
        return [x.name for x in self._items]

    @property
    def active(self) -> "Groups":
        """A group is active when its `conditions` are met"""
        return Groups([x for x in self._data if x["is_active"]])

    @property
    def inactive(self) -> "Groups":
        """A group is inactive when its `conditions` are not met"""
        return Groups([x for x in self._data if not x["is_active"]])

    @property
    def passing(self) -> "Groups":
        """A group is passing if it is \"active\" and \"approved\", or is \"inactive\" """
        return Groups([x for x in self._data if x["is_passing"]])

    @property
    def approved(self) -> "Groups":
        """A group is approved when it has the number of approvals `required`"""
        return Groups([x for x in self._data if x["state"] == "approved"])

    @property
    def pending(self) -> "Groups":
        """A group is "pending" if it does not have the number of approvals `required`"""
        return Groups([x for x in self._data if x["state"] == "pending"])

    @property
    def rejected(self) -> "Groups":
        """A group is "rejected" if any reviewer in the group has rejected the pull request"""
        return Groups([x for x in self._data if x["state"] == "rejected"])

    @property
    def optional(self) -> "Groups":
        """A group is optional if the `type` is \"optional\" """
        return Groups([x for x in self._data if x["type"] == "optional"])

    @property
    def required(self) -> "Groups":
        """A group is optional if the `type` is \"required\" """
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
