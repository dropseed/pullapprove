from typing import TYPE_CHECKING, List

from cached_property import cached_property

from .base import ContextObject, ContextObjectList

if TYPE_CHECKING:
    from pullapprove.models.gitlab.merge_request import (
        MergeRequest as MergeRequestModel,
    )


class User(ContextObject):
    """A GitLab user."""

    _eq_attr = "username"
    _contains_attr = "username"


class Users(ContextObjectList):
    _item_type = User
    _eq_attr = "usernames"
    _contains_attr = "usernames"

    @property
    def usernames(self) -> List[str]:
        return [x.username for x in self._items]


class Milestone(ContextObject):
    _eq_attr = "title"
    _contains_attr = "title"


class Pipeline(ContextObject):
    _eq_attr = "id"
    _contains_attr = "id"


class Diff(ContextObject):
    """A git diff for the MR"""

    _eq_attr = "diff"
    _contains_attr = "diff"

    @classmethod
    def from_pull_request(cls, pull_request: "MergeRequestModel") -> "Diff":
        obj = cls({})
        obj._merge_request = pull_request  # type: ignore
        return obj

    @cached_property
    def diff(self) -> str:
        """The git diff as a string"""
        return "\n".join([x["diff"] for x in self._merge_request.diffs])  # type: ignore

    @property
    def lines_added(self) -> List[str]:
        """Lines from git diff that start with "+"""
        return [x[1:] for x in self.diff.splitlines() if x.startswith("+")]

    @property
    def lines_removed(self) -> List[str]:
        """Lines from git diff that start with "-"""
        return [x[1:] for x in self.diff.splitlines() if x.startswith("-")]

    @property
    def lines_modified(self) -> List[str]:
        """Combination of `lines_added` and `lines_modified`"""
        return self.lines_added + self.lines_removed


class MergeRequest(ContextObject):
    _eq_attr = "id"
    _contains_attr = "title"
    _subtypes = {
        "author": User,
        "assignee": User,
        "assignees": Users,
        "reviewers": Users,
        "milestone": Milestone,
        "merged_by": User,
        "pipeline": Pipeline,
    }

    def __init__(self, pull_request_obj: "MergeRequestModel") -> None:
        self._pull_request_obj = pull_request_obj
        data = pull_request_obj.data
        self.diff = Diff.from_pull_request(pull_request_obj)
        super().__init__(data)

    def _available_keys(self) -> List[str]:
        keys = dir(self)
        keys += list(self._data.keys())
        keys += list(self._children.keys())
        key_set = set(keys)
        return [x for x in key_set if not x.startswith("_")]

    @property
    def number(self) -> int:
        return self.iid  # type: ignore
