import re
from typing import TYPE_CHECKING, List

from cached_property import cached_property

from .base import ContextObject, ContextObjectList

if TYPE_CHECKING:
    from pullapprove.models.bitbucket.pull_request import (
        PullRequest as PullRequestModel,
    )


class Account(ContextObject):
    _eq_attr = "nickname"
    _contains_attr = "nickname"


class Accounts(ContextObjectList):
    _item_type = Account
    _eq_attr = "nicknames"
    _contains_attr = "nicknames"

    @property
    def nicknames(self) -> List[str]:
        return [x.nickname for x in self._items]  # type: ignore


class Participant(ContextObject):
    _eq_attr = "nickname"
    _contains_attr = "nickname"
    _subtypes = {
        "user": Account,
    }

    @property
    def nickname(self) -> str:
        return self.user.nickname  # type: ignore


class Participants(ContextObjectList):
    _eq_attr = "nicknames"
    _contains_attr = "nicknames"
    _item_type = Participant

    @property
    def nicknames(self) -> List[str]:
        return [x.nickname for x in self._items]


class Repository(ContextObject):
    _eq_attr = "full_name"
    _contains_attr = "full_name"


class Branch(ContextObject):
    _eq_attr = "name"
    _contains_attr = "name"


class Commit(ContextObject):
    _eq_attr = "hash"
    _contains_attr = "hash"

    @property
    def user(self) -> Account:
        return Account(self._data["author"]["user"])


class Commits(ContextObjectList):
    _eq_attr = "hashes"
    _contains_attr = "hashes"
    _item_type = Commit

    @classmethod
    def from_pull_request(cls, pull_request: "PullRequestModel") -> "Commits":
        obj = cls([])
        obj._fetch_remote_data = lambda: pull_request.commits
        return obj

    @property
    def hashes(self) -> List[str]:
        return [x.hash for x in self._items]


class PullRequestEndpoint(ContextObject):
    _eq_attr = "branch_name"
    _contains_attr = "branch_name"
    _subtypes = {
        "repository": Repository,
        "branch": Branch,
        "commit": Commit,
    }

    @property
    def branch_name(self) -> str:
        return self.branch.name  # type: ignore


class Comment(ContextObject):
    _eq_attr = "id"
    _contains_attr = "markdown"
    _subtypes = {
        "user": Account,
    }

    @property
    def markdown(self) -> str:
        return self._data["content"]["raw"]


class Comments(ContextObjectList):
    _eq_attr = "ids"
    _contains_attr = "ids"
    _item_type = Comment

    @classmethod
    def from_pull_request(cls, pull_request: "PullRequestModel") -> "Comments":
        obj = cls([])
        obj._fetch_remote_data = lambda: pull_request.comments
        return obj

    @property
    def ids(self) -> List[str]:
        return [x.id for x in self._items]


class Diffstat(ContextObject):
    _eq_attr = "path"
    _contains_attr = "path"

    @property
    def path(self) -> str:
        if "new" in self._data:
            return self._data["new"]["path"]
        elif "old" in self._data:
            return self._data["old"]["path"]
        return ""


class Diffstats(ContextObjectList):
    _eq_attr = "paths"
    _contains_attr = "paths"
    _item_type = Diffstat

    @classmethod
    def from_pull_request(cls, pull_request: "PullRequestModel") -> "Diffstats":
        obj = cls([])
        obj._fetch_remote_data = lambda: pull_request.diffstat
        return obj

    @property
    def paths(self) -> List[str]:
        return [x.path for x in self._items]

    @property
    def added(self) -> "Diffstats":
        """Diffstats for added files"""
        return Diffstats([x._data for x in self._items if x.status == "added"])

    @property
    def removed(self) -> "Diffstats":
        """Diffstats for removed files"""
        return Diffstats([x._data for x in self._items if x.status == "removed"])

    @property
    def modified(self) -> "Diffstats":
        """Diffstats for modified files"""
        return Diffstats([x._data for x in self._items if x.status == "modified"])

    @property
    def renamed(self) -> "Diffstats":
        """Diffstats for renamed files"""
        return Diffstats([x._data for x in self._items if x.status == "renamed"])


class Status(ContextObject):
    _eq_attr = "key"
    _contains_attr = "key"


class Statuses(ContextObjectList):
    _eq_attr = "keys"
    _contains_attr = "keys"
    _item_type = Status

    @classmethod
    def from_pull_request(cls, pull_request: "PullRequestModel") -> "Statuses":
        obj = cls([])
        obj._fetch_remote_data = lambda: pull_request.statuses
        return obj

    @property
    def keys(self) -> List[str]:
        return [x.key for x in self._items]

    @property
    def successful(self) -> "Statuses":
        """Statuses that are SUCCESSFUL"""
        return Statuses([x._data for x in self._items if x.state == "SUCCESSFUL"])

    @property
    def failed(self) -> "Statuses":
        """Statuses that are FAILED"""
        return Statuses([x._data for x in self._items if x.state == "FAILED"])

    @property
    def in_progress(self) -> "Statuses":
        """Statuses that are INPROGRESS"""
        return Statuses([x._data for x in self._items if x.state == "INPROGRESS"])

    @property
    def stopped(self) -> "Statuses":
        """Statuses that are STOPPED"""
        return Statuses([x._data for x in self._items if x.state == "STOPPED"])


# Diff is just text in the API, but we'll wrap it to add methods
class Diff(ContextObject):
    _eq_attr = "diff"
    _contains_attr = "diff"

    @property
    def diff(self) -> str:
        return self._data["diff"]

    @property
    def lines_added(self) -> List[str]:
        return [x[1:] for x in self.diff.splitlines() if x.startswith("+")]

    @property
    def lines_removed(self) -> List[str]:
        return [x[1:] for x in self.diff.splitlines() if x.startswith("-")]

    @property
    def lines_modified(self) -> List[str]:
        return self.lines_added + self.lines_removed


class PullRequest(ContextObject):
    _eq_attr = "id"
    _contains_attr = "title"
    _subtypes = {
        "author": Account,
        "source": PullRequestEndpoint,
        "destination": PullRequestEndpoint,
        "closed_by": Account,
        "reviewers": Accounts,
        "participants": Participants,
        "merge_commit": Commit,
    }

    def __init__(self, pull_request_obj: "PullRequestModel") -> None:
        data = pull_request_obj.data
        self.comments = Comments.from_pull_request(pull_request_obj)
        self.commits = Commits.from_pull_request(pull_request_obj)
        self.diffstat = Diffstats.from_pull_request(pull_request_obj)
        self.statuses = Statuses.from_pull_request(pull_request_obj)
        self._fetch_diff = lambda: pull_request_obj.diff
        super().__init__(data)

    @cached_property
    def diff(self) -> "Diff":
        return Diff({"diff": self._fetch_diff()})

    def _available_keys(self) -> List[str]:
        keys = dir(self)
        keys += list(self._data.keys())
        keys += list(self._children.keys())
        key_set = set(keys)
        return [x for x in key_set if not x.startswith("_")]
