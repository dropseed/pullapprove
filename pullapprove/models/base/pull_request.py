import os
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import quote

from cached_property import cached_property

from pullapprove.logger import logger
from pullapprove.models.events import Events
from pullapprove.models.groups import Group
from pullapprove.models.reviews import Reviewers
from pullapprove.models.states import State
from pullapprove.models.status import Status
from pullapprove.storage import Storage

from .repo import BaseRepo

UI_BASE_URL = os.environ.get("UI_BASE_URL", None)


class BasePullRequest:
    def __init__(self, repo: BaseRepo, number: int) -> None:
        self.repo = repo
        self.number = number
        self.events = Events()

    def as_dict(self) -> Dict[str, Any]:
        # Report should be able to depend on these keys
        return {"number": self.number}

    def as_context(self) -> Dict[str, Any]:
        raise NotImplementedError

    @cached_property
    def data(self) -> Dict[str, Any]:
        raise NotImplementedError

    @property
    def base_ref(self) -> str:
        raise NotImplementedError

    @property
    def author(self) -> str:
        raise NotImplementedError

    @property
    def reviewers(self) -> Reviewers:
        raise NotImplementedError

    @property
    def users_requested(self) -> List[str]:
        raise NotImplementedError

    @property
    def users_unreviewable(self) -> List[str]:
        """Platform dependant list of users who can't review"""
        return []

    def set_labels(
        self, labels_to_add: List[str], labels_to_remove: List[str]
    ) -> List[str]:
        raise NotImplementedError

    def set_reviewers(
        self, users_to_add: List[str], users_to_remove: List[str], total_required: int
    ) -> None:
        raise NotImplementedError

    def create_comment(self, body: str, ignore_mode: bool = False) -> None:
        raise NotImplementedError

    def create_or_update_comment(self, body: str, comment_id: str) -> None:
        raise NotImplementedError

    def send_status(self, status: Status, output_data: Dict[str, Any]) -> Optional[str]:
        raise NotImplementedError

    @cached_property
    def latest_status(self) -> Optional[Status]:
        raise NotImplementedError

    def store_report(self, data: Dict[str, Any]) -> str:
        report_url = ""

        key = data["meta"]["id"]
        fingerprint = data["meta"]["fingerprint"]

        if UI_BASE_URL:
            try:
                storage = Storage()
                url = storage.store_data(f"reports/{key}.json", data)
                if url:
                    json_url = quote(url)
                    report_url = (
                        f"{UI_BASE_URL}?url={json_url}&fingerprint={fingerprint}"
                    )
            except Exception as e:
                # if storage fails somehow, let it continue but don't
                # add the url to the status, otherwise it will try to send a fail
                # status but just fail again because it can't use storage...
                # likely a config error more than anything, and sentry will report
                logger.error(e, exc_info=e)

        return report_url

    def calculate_status(
        self, groups: List[Group], users_unavailable: List[str] = []
    ) -> Tuple[Status, Callable]:
        """Combines the config settings, with data from this PR, and returns a Status object"""

        users_unavailable = users_unavailable + self.users_unreviewable

        users_to_request: Set[str] = set()
        users_to_unrequest: Set[str] = set()

        labels_to_add: Set[str] = set()
        labels_to_remove: Set[str] = set()

        # a group can only reference groups that have been processed before it
        preceeding_groups_data: List[Dict] = []

        for group in groups:
            group.load_pr(
                self,
                preceeding_groups_data[
                    :
                ],  # make a copy of this obj, don't pass the reference (mostly for test cases)
                users_unavailable,
                users_already_requested=list(users_to_request),
            )

            if group.users_to_request:
                users_to_request.update(group.users_to_request)
                self.events.add(
                    "pullapprove.group.requested_reviewers",
                    {
                        "group": group.as_dict(),
                        "requested_reviewers": [
                            {"login": x} for x in group.users_to_request
                        ],
                    },
                )

            if group.users_to_unrequest:
                users_to_unrequest.update(group.users_to_unrequest)
                self.events.add(
                    "pullapprove.group.unrequested_reviewers",
                    {
                        "group": group.as_dict(),
                        "unrequested_reviewers": [
                            {"login": x} for x in group.users_to_unrequest
                        ],
                    },
                )

            if group.is_active:
                labels = group.labels.copy()
                active_label = labels.pop(group.state, "")
                inactive_labels = [x for x in labels.values() if x]

                if active_label:
                    labels_to_add.add(active_label)
                if inactive_labels:
                    labels_to_remove.update(inactive_labels)
            else:
                labels_to_remove.update([x for x in group.labels.values() if x])

            preceeding_groups_data.append(group.as_dict())

        # let the platform decide whether to do this or not (total might need to be updatd on gitlab even if users don't)
        total_required = sum([x.required - x.bonus for x in groups if x.is_active])

        def before_status_send():
            self.set_reviewers(
                users_to_add=list(users_to_request),
                users_to_remove=list(users_to_unrequest),
                total_required=total_required,
            )

            if labels_to_add or labels_to_remove:
                self.set_labels(list(labels_to_add), list(labels_to_remove))

        return Status.from_groups(groups), before_status_send
