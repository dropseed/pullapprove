import os
import random
import time
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from cached_property import cached_property

import pullapprove.context.functions
import pullapprove.context.github
from pullapprove.logger import canonical, logger
from pullapprove.models.base import BasePullRequest

from ..reviews import Review, Reviewers
from ..states import ReviewState
from ..status import Status
from .states import (
    GITHUB_REVIEW_STATE_TO_PULLAPPROVE_REVIEW_STATE,
    GITHUB_STATUS_STATE_TO_PULLAPPROVE_STATUS_STATE,
    PULLAPPROVE_STATUS_STATE_TO_GITHUB_STATUS_STATE,
)

GITHUB_STATUS_CONTEXT = os.environ.get("GITHUB_STATUS_CONTEXT", "pullapprove")


class PullRequest(BasePullRequest):
    def as_context(self) -> Dict[str, Any]:
        pull_request = pullapprove.context.github.PullRequest(self)
        return {
            **pullapprove.context.functions.get_context_dictionary(self.number),
            # make these available at the top level, not under "pullrequest.key" or something
            **{x: getattr(pull_request, x) for x in pull_request._available_keys()},
        }

    def send_status(self, status: Status, output_data: Dict[str, Any]) -> Optional[str]:
        data = {
            "state": PULLAPPROVE_STATUS_STATE_TO_GITHUB_STATUS_STATE[status.state],
            "description": status.description[:140],
            "target_url": None,
            "context": GITHUB_STATUS_CONTEXT,
        }

        if (
            self.repo.api.mode.is_live()  # Check live because if we're testing, we always need to save the report
            and self.latest_status
            and self.latest_status.is_the_same_as(
                data["state"], data["description"], output_data["meta"]["fingerprint"]
            )
        ):
            return None

        report_url = self.store_report(output_data)
        if report_url:
            data["target_url"] = report_url

        self.repo.api.post(f"/statuses/{self.latest_sha}", json=data)

        return report_url

    def set_reviewers(
        self, users_to_add: List[str], users_to_remove: List[str], total_required: int
    ) -> None:
        if users_to_add:
            self._request_reviewers(users_to_add)

        if users_to_remove:
            self._unrequest_reviewers(users_to_remove)

    def _unrequest_reviewers(self, users: List[str]) -> None:
        if self.data["state"] == "closed":
            logger.info("Not sending review requests for closed PR")
            return

        self.repo.api.delete(
            f"/pulls/{self.number}/requested_reviewers", json={"reviewers": users}
        )

    def _request_reviewers(self, users: List[str]) -> None:
        if self.data["state"] == "closed":
            logger.info("Not sending review requests for closed PR")
            return

        # Temporary fix for the (rare) race condition in the GitHub API
        # where duplicate reviews are created, causing notifications, etc.
        delay = random.uniform(0, 1)
        time.sleep(delay)

        self.repo.api.post(
            f"/pulls/{self.number}/requested_reviewers",
            json={"reviewers": users},
            user_error_status_codes={422: "Given usernames could not be requested."},
        )

    @cached_property
    def data(self) -> Dict[str, Any]:
        headers: Dict[str, str] = {}

        if any([event.name.startswith("pull_request.") for event in self.events]):
            # make sure we don't get stale data
            # if it looks like the pull_request was just changed
            headers = {"Cache-Control": "max-age=1, min-fresh=1"}

        return self.repo.api.get(f"/pulls/{self.number}", headers=headers)

    @property
    def base_ref(self) -> str:
        return self.data["base"]["ref"]

    @property
    def author(self) -> str:
        return self.data["user"]["login"]

    @property
    def latest_sha(self) -> str:
        return self.data["head"]["sha"]

    @cached_property
    def reviews(self) -> Dict[str, Any]:
        return self.repo.api.get(
            f"/pulls/{self.number}/reviews",
            headers={"Cache-Control": "max-age=1, min-fresh=1"},
        )

    @cached_property
    def requested_reviewers(self) -> Dict[str, Any]:
        return self.repo.api.get(
            f"/pulls/{self.number}/requested_reviewers",
            headers={"Cache-Control": "max-age=1, min-fresh=1"},
        )

    @property
    def reviewers(self) -> Reviewers:
        reviewers = Reviewers()

        for review in self.reviews:
            if not review["user"]:
                # a user can be deleted, evidently
                continue

            username = review["user"]["login"]
            state = review["state"]
            body = review["body"]

            if state in GITHUB_REVIEW_STATE_TO_PULLAPPROVE_REVIEW_STATE:
                state = GITHUB_REVIEW_STATE_TO_PULLAPPROVE_REVIEW_STATE[state]
            elif (
                state == "COMMENTED"
                and username not in [x.username for x in reviewers]
                and username
                != self.author  # these could be /commands or other random comments (authors can't actually approve in github)
            ):
                # the comment is their first review, which we will consider as pending
                # (fixes the issue where they were a requested_reviewer, and then only left a comment review, which triggered a new request to go out)
                # - if they have submitted a valid review before this, we want to ignore the comment
                # - if they submit a valid review after this, it will update the state
                state = ReviewState.PENDING
            else:
                # skip anything else (COMMENTED -- neutral)
                continue

            review = Review(state=state, body=body)
            reviewers.append_review(username=username, review=review)

        # TODO should self.users_requested really be in here as PENDING instead?
        # what's the difference between pending and requested...

        return reviewers

    @property
    def users_requested(self) -> List[str]:
        return [x["login"] for x in self.requested_reviewers["users"]]

    @property
    def users_unreviewable(self) -> List[str]:
        # authors can't review on github
        return [self.author]

    def _get_statuses(self) -> List[Dict[str, Any]]:
        """Gets the latest status for each context"""
        return self.repo.api.get(
            f"/commits/{self.latest_sha}/status",
            headers={"Cache-Control": "max-age=1, min-fresh=1"},
            page_items_key="statuses",
        )

    @cached_property
    def statuses(self) -> List[Dict[str, Any]]:
        return self._get_statuses()

    @cached_property
    def latest_status(self) -> Optional[Status]:
        statuses = self._get_statuses()

        # statuses can appear multiple times per commit, but the most
        # recent will be first which is what we want
        for status in statuses:
            if status["context"] == GITHUB_STATUS_CONTEXT:
                return Status(
                    state=GITHUB_STATUS_STATE_TO_PULLAPPROVE_STATUS_STATE[
                        status["state"]
                    ],
                    description=status["description"],
                    groups=[],  # unknown... but we could potentially parse back off URL...
                    report_url=status["target_url"],
                )

        return None

    @cached_property
    def check_runs(self) -> List[Dict[str, Any]]:
        return self.repo.api.get(
            f"/commits/{self.latest_sha}/check-runs",
            headers={"Cache-Control": "max-age=1, min-fresh=1"},
            page_items_key="check_runs",
        )

    @cached_property
    def files(self) -> List[Dict[str, Any]]:
        # TODO raise exception if files not ready,
        # catch and send error status and msg to try again in a minute?
        return self.repo.api.get(f"/pulls/{self.number}/files")

    @cached_property
    def commits(self) -> List[Dict[str, Any]]:
        return self.repo.api.get(f"/pulls/{self.number}/commits")

    def create_comment(self, body: str, ignore_mode: bool = False) -> None:
        self.repo.api.post(
            f"/issues/{self.number}/comments",
            json={"body": body},
            ignore_mode=ignore_mode,
        )

    def create_or_update_comment(self, body: str, comment_id: str) -> None:
        header_string = f"<!-- PullApprove ID: {comment_id} -->"
        body_with_header = header_string + "\n" + body
        existing_comment = None

        for comment in self.repo.api.get(
            f"/issues/{self.number}/comments",
            headers={"Cache-Control": "max-age=1, min-fresh=1"},
        ):
            if comment["body"].startswith(header_string):
                existing_comment = comment
                break

        if existing_comment:
            self.repo.api.patch(
                existing_comment["url"],
                json={"body": body_with_header},
            )
        else:
            self.create_comment(body_with_header)

    def set_labels(
        self, labels_to_add: List[str], labels_to_remove: List[str]
    ) -> List[str]:
        current_labels = set([x["name"] for x in self.data["labels"]])

        # labels are removed, THEN added so that if there are duplicates across groups,
        # they end up being added if they are supposed to be present
        updated_labels = current_labels - set(labels_to_remove)
        updated_labels = updated_labels | set(labels_to_add)

        logger.debug(
            f"github.set_labels labels_to_add={labels_to_add} labels_to_remove={labels_to_remove} current_labels={list(current_labels)} updated_labels={list(updated_labels)}"
        )

        if updated_labels != current_labels:
            self.repo.api.put(
                f"/issues/{self.number}/labels",
                json={"labels": list(updated_labels)},
                user_error_status_codes={422: None},
            )

        return list(updated_labels)
