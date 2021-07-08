import re
from typing import TYPE_CHECKING, List

from .base import ContextObject, ContextObjectList

if TYPE_CHECKING:
    from pullapprove.models.bitbucket.pull_request import (
        PullRequest as PullRequestModel,
    )


class PullRequest(ContextObject):
    _eq_attr = "id"
    _contains_attr = "title"
    # _subtypes = {
    #     "user": User,
    #     "assignee": User,
    #     "assignees": Users,
    #     "requested_reviewers": Users,
    #     "requested_teams": Teams,
    #     "labels": Labels,
    #     "milestone": Milestone,
    #     "head": Branch,
    #     "base": Branch,
    #     "merged_by": User,
    # }

    def __init__(self, pull_request_obj: "PullRequestModel") -> None:
        data = pull_request_obj.data
        super().__init__(data)

    # @property
    # def author(self) -> User:
    #     return self.user  # type: ignore

    def _available_keys(self) -> List[str]:
        keys = dir(self)
        keys += list(self._data.keys())
        keys += list(self._children.keys())
        key_set = set(keys)
        return [x for x in key_set if not x.startswith("_")]
