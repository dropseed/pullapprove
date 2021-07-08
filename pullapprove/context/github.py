import re
from typing import TYPE_CHECKING, List

from .base import ContextObject, ContextObjectList

if TYPE_CHECKING:
    from pullapprove.models.github.pull_request import PullRequest as PullRequestModel


class User(ContextObject):
    _eq_attr = "login"
    _contains_attr = "login"

    @property
    def username(self) -> str:
        return self.login  # type: ignore

    @property
    def mention(self) -> str:
        """@username"""
        return f"@{self.login}"  # type: ignore


class Users(ContextObjectList):
    _eq_attr = "usernames"
    _contains_attr = "usernames"
    _item_type = User

    @property
    def usernames(self) -> List[str]:
        return [x.username for x in self._items]  # type: ignore

    @property
    def mentions(self) -> List[str]:
        """List of @usernames"""
        return [x.mention for x in self._items]  # type: ignore


class File(ContextObject):
    _eq_attr = "filename"
    _contains_attr = "filename"


class Files(ContextObjectList):
    """
    [See the GitHub documentation for more information.](https://developer.github.com/v3/pulls/#list-pull-requests-files)
    """

    _eq_attr = "filenames"
    _contains_attr = "filenames"
    _item_type = File

    @classmethod
    def from_pull_request(cls, pull_request: "PullRequestModel") -> "Files":
        obj = cls([])
        obj._fetch_remote_data = lambda: pull_request.files
        return obj

    @property
    def filenames(self) -> List[str]:
        return [x.filename for x in self._items]

    @property
    def patches(self) -> List[str]:
        # Not all file objects have patches (ex. new PNG)
        # GitHub leaves this property off completely, oddly
        return [x.patch for x in self._items if hasattr(x, "patch")]

    @property
    def lines_added(self) -> List[str]:
        lines = []
        for patch in self.patches:
            lines += [x[1:] for x in patch.splitlines() if x.startswith("+")]
        return lines

    @property
    def lines_removed(self) -> List[str]:
        lines = []
        for patch in self.patches:
            lines += [x[1:] for x in patch.splitlines() if x.startswith("-")]
        return lines

    @property
    def lines_modified(self) -> List[str]:
        return self.lines_added + self.lines_removed

    @property
    def added(self) -> "Files":
        return Files([x._data for x in self._items if x.status == "added"])

    @property
    def modified(self) -> "Files":
        return Files([x._data for x in self._items if x.status == "modified"])

    @property
    def removed(self) -> "Files":
        return Files([x._data for x in self._items if x.status == "removed"])


class Status(ContextObject):
    _eq_attr = "context"
    _contains_attr = "context"


class Statuses(ContextObjectList):
    """
    Statuses are pulled from the most recent commit on the pull request.
    [See the GitHub documentation for more information.](https://developer.github.com/v3/repos/statuses/#list-statuses-for-a-specific-ref)
    """

    _eq_attr = "contexts"
    _contains_attr = "contexts"
    _item_type = Status

    @classmethod
    def from_pull_request(cls, pull_request: "PullRequestModel") -> "Statuses":
        obj = cls([])
        obj._fetch_remote_data = lambda: pull_request.statuses
        return obj

    @property
    def contexts(self) -> List[str]:
        return list(set([x.context for x in self._items]))

    @property
    def failed(self) -> "Statuses":
        return Statuses([x._data for x in self._items if x.state == "failure"])

    @property
    def pending(self) -> "Statuses":
        return Statuses([x._data for x in self._items if x.state == "pending"])

    @property
    def errored(self) -> "Statuses":
        return Statuses([x._data for x in self._items if x.state == "error"])

    @property
    def successful(self) -> "Statuses":
        return Statuses([x._data for x in self._items if x.state == "success"])

    @property
    def succeeded(self) -> "Statuses":
        return self.successful


class CheckRun(ContextObject):
    _eq_attr = "name"
    _contains_attr = "name"


class CheckRuns(ContextObjectList):
    """
    Checks runs are pulled from the most recent commit on the pull request.
    Results of GitHub Actions are found here.
    [See the GitHub documentation for more information.](https://docs.github.com/en/free-pro-team@latest/rest/reference/checks#list-check-runs-for-a-git-reference)
    """

    _eq_attr = "names"
    _contains_attr = "names"
    _item_type = CheckRun

    @classmethod
    def from_pull_request(cls, pull_request: "PullRequestModel") -> "CheckRuns":
        obj = cls([])
        obj._fetch_remote_data = lambda: pull_request.check_runs
        return obj

    @property
    def names(self) -> List[str]:
        return list(set([x.name for x in self._items]))

    @property
    def success(self) -> "CheckRuns":
        """
        Alias for `.successful`
        """
        return self.successful

    @property
    def successful(self) -> "CheckRuns":
        return CheckRuns([x._data for x in self._items if x.conclusion == "success"])

    @property
    def failure(self) -> "CheckRuns":
        """
        Alias for `.failed`
        """
        return self.failed

    @property
    def failed(self) -> "CheckRuns":
        return CheckRuns([x._data for x in self._items if x.conclusion == "failure"])

    @property
    def neutral(self) -> "CheckRuns":
        return CheckRuns([x._data for x in self._items if x.conclusion == "neutral"])

    @property
    def cancelled(self) -> "CheckRuns":
        return CheckRuns([x._data for x in self._items if x.conclusion == "cancelled"])

    @property
    def skipped(self) -> "CheckRuns":
        return CheckRuns([x._data for x in self._items if x.conclusion == "skipped"])

    @property
    def timed_out(self) -> "CheckRuns":
        return CheckRuns([x._data for x in self._items if x.conclusion == "timed_out"])

    @property
    def action_required(self) -> "CheckRuns":
        return CheckRuns(
            [x._data for x in self._items if x.conclusion == "action_required"]
        )

    @property
    def stale(self) -> "CheckRuns":
        return CheckRuns([x._data for x in self._items if x.conclusion == "stale"])

    @property
    def queued(self) -> "CheckRuns":
        return CheckRuns([x._data for x in self._items if x.status == "queued"])

    @property
    def in_progress(self) -> "CheckRuns":
        return CheckRuns([x._data for x in self._items if x.status == "in_progress"])

    @property
    def completed(self) -> "CheckRuns":
        return CheckRuns([x._data for x in self._items if x.status == "completed"])


class Commit(ContextObject):
    _eq_attr = "sha"
    _contains_attr = "message"

    @property
    def message(self) -> str:
        return self._data["commit"]["message"]

    @property
    def is_signed_off(self) -> bool:
        """
        Whether the commit message has a "Signed-off-by:" line containing
        the email address of the commit author.

        Can be used for [Developer Certificate of Origin (DCO)](https://developercertificate.org/).
        """
        msg = self._data["commit"]["message"]
        email = self._data["commit"]["author"]["email"]

        # get the text after "Signed-off-by:"
        found = re.findall("(?<=Signed-off-by:)(.*)", msg)

        for line_match in found:
            # just check that the author email is somewhere in rest of the line
            if email.lower() in line_match.lower():
                return True

        return False


class Commits(ContextObjectList):
    _eq_attr = "shas"
    _contains_attr = "shas"
    _item_type = Commit

    @classmethod
    def from_pull_request(cls, pull_request: "PullRequestModel") -> "Commits":
        obj = cls([])
        obj._fetch_remote_data = lambda: pull_request.commits
        return obj

    @property
    def shas(self) -> List[str]:
        return [x.sha for x in self._items]

    @property
    def are_signed_off(self) -> bool:
        return all([x.is_signed_off for x in self._items])


class Label(ContextObject):
    _eq_attr = "name"
    _contains_attr = "name"


class Labels(ContextObjectList):
    _eq_attr = "names"
    _contains_attr = "names"
    _item_type = Label

    @property
    def names(self) -> List[str]:
        return [x.name for x in self._items]  # type: ignore


class Milestone(ContextObject):
    _eq_attr = "title"
    _contains_attr = "title"
    _subtypes = {"creator": User}


class Repo(ContextObject):
    _eq_attr = "full_name"
    _contains_attr = "full_name"
    _subtypes = {"owner": User}


class Branch(ContextObject):
    _eq_attr = "label"
    _contains_attr = "label"
    _subtypes = {"user": User, "repo": Repo}


class Review(ContextObject):
    _eq_attr = "id"
    _contains_attr = "body"
    _subtypes = {"user": User}


class Comment(ContextObject):
    _eq_attr = "id"
    _contains_attr = "body"
    _subtypes = {"user": User}


class Team(ContextObject):
    _eq_attr = "id"
    _contains_attr = "name"


class Teams(ContextObjectList):
    _eq_attr = "ids"
    _contains_attr = "names"
    _item_type = Team

    @property
    def ids(self) -> List[int]:
        return [x.id for x in self._items]  # type: ignore

    @property
    def names(self) -> List[str]:
        return [x.name for x in self._items]  # type: ignore


class PullRequest(ContextObject):
    _eq_attr = "number"
    _contains_attr = "title"
    _subtypes = {
        "user": User,
        "assignee": User,
        "assignees": Users,
        "requested_reviewers": Users,
        "requested_teams": Teams,
        "labels": Labels,
        "milestone": Milestone,
        "head": Branch,
        "base": Branch,
        "merged_by": User,
    }

    def __init__(self, pull_request_obj: "PullRequestModel") -> None:
        data = pull_request_obj.data
        self.files = Files.from_pull_request(pull_request_obj)
        self.statuses = Statuses.from_pull_request(pull_request_obj)
        self.check_runs = CheckRuns.from_pull_request(pull_request_obj)
        data.pop("commits", 0)  # GH already has a commits key, but it's just an int
        self.commits = Commits.from_pull_request(pull_request_obj)
        super().__init__(data)

    @property
    def author(self) -> User:
        return self.user  # type: ignore

    def _available_keys(self) -> List[str]:
        keys = dir(self)
        keys += list(self._data.keys())
        keys += list(self._children.keys())
        key_set = set(keys)
        return [x for x in key_set if not x.startswith("_")]
