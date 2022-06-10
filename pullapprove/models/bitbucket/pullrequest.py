from typing import Any, Dict, List, Optional

from cached_property import cached_property

import pullapprove.context.functions
from pullapprove.context.bitbucket import PullRequest as PullRequestContext
from pullapprove.exceptions import UserError
from pullapprove.models.base import BasePullRequest
from pullapprove.settings import settings

from ..reviews import Review, Reviewers
from ..states import ReviewState
from ..status import Status
from .states import (
    BITBUCKET_REVIEW_STATE_TO_PULLAPPROVE_REVIEW_STATE,
    BITBUCKET_STATUS_STATE_TO_PULLAPPROVE_STATUS_STATE,
    PULLAPPROVE_STATUS_STATE_TO_BITBUCKET_STATUS_STATE,
)

BITBUCKET_STATUS_KEY = settings.get("BITBUCKET_STATUS_KEY", "pullapprove")


class PullRequest(BasePullRequest):
    def as_context(self) -> Dict[str, Any]:
        pull_request = PullRequestContext(self)
        return {
            **pullapprove.context.functions.get_context_dictionary(self.number),
            # make these available at the top level, not under "pullrequest.key" or something
            **{x: getattr(pull_request, x) for x in pull_request._available_keys()},
        }

    @cached_property
    def data(self) -> Dict[str, Any]:
        headers: Dict[str, str] = {}

        if any([event.name.startswith("pullrequest:") for event in self.events]):
            # make sure we don't get stale data
            # if it looks like the pull_request was just changed
            headers = {"Cache-Control": "max-age=1, min-fresh=1"}

        return self.repo.api.get(f"/pullrequests/{self.number}", headers=headers)

    @property
    def reviewers(self) -> Reviewers:
        reviewers = Reviewers()

        # These are people requested on the PR
        for reviewer in self.data["reviewers"]:
            review = Review(state=ReviewState.PENDING, body="")
            reviewers.append_review(username=reviewer["nickname"], review=review)

        # These are the people who've actually done something
        for participant in self.data["participants"]:
            if (
                participant["state"]
                in BITBUCKET_REVIEW_STATE_TO_PULLAPPROVE_REVIEW_STATE
            ):
                state = BITBUCKET_REVIEW_STATE_TO_PULLAPPROVE_REVIEW_STATE[
                    participant["state"]
                ]
            else:
                continue

            review = Review(state=state, body="")
            reviewers.append_review(
                username=participant["user"]["nickname"], review=review
            )

        return reviewers

    def set_reviewers(
        self, users_to_add: List[str], users_to_remove: List[str], total_required: int
    ) -> None:
        # First, use the strings in users_to_add to see if we can match
        # to a workspace member by account_id, uuid, or nickname
        # (writing it this way so we can error if we can't find a user)
        reviewers_to_add = [
            x["user"]
            for x in self.repo.workspace_members  # type: ignore
            if x["user"]["account_id"] in users_to_add
            or x["user"]["uuid"] in users_to_add
            or x["user"]["nickname"] in users_to_add
        ]

        if len(reviewers_to_add) != len(users_to_add):
            raise UserError(f"Users not found in workspace: {users_to_add}")

        # Add the new reviewers to the current ones on the PR
        updated_reviewers = self.data["reviewers"] + reviewers_to_add

        # Last, remove anyone in users_to_remove
        updated_reviewers = [
            x
            for x in updated_reviewers
            if x["account_id"] not in users_to_remove
            and x["uuid"] not in users_to_remove
            and x["nickname"] not in users_to_remove
        ]

        if set(x["account_id"] for x in self.data["reviewers"]) == set(
            x["account_id"] for x in updated_reviewers
        ):
            # Nothing has changed
            return updated_reviewers

        self.repo.api.put(
            f"/pullrequests/{self.number}",
            json={
                "reviewers": [{"uuid": x["uuid"]} for x in updated_reviewers],
                # Has to have the title field to be valid...
                "title": self.data["title"],
            },
        )

        # Return is just for testing right now - mypy doesn't seem to care
        # and don't want to implement on GitHub/GitLab yet for no reason
        return updated_reviewers

    @property
    def users_requested(self) -> List[str]:
        return [x["nickname"] for x in self.data["reviewers"]]

    @property
    def base_ref(self) -> str:
        return self.data["destination"]["branch"]["name"]

    @property
    def author(self) -> str:
        return self.data["author"]["nickname"]

    @property
    def users_unreviewable(self) -> List[str]:
        # authors can't be an assigned reviewer on bitbucket
        return [self.author]

    @cached_property
    def latest_status(self) -> Optional[Status]:
        try:
            status = self.repo.api.get(
                f"/commit/{self.data['source']['commit']['hash']}/statuses/build/{BITBUCKET_STATUS_KEY}",
                user_error_status_codes={404: None},
            )
        except UserError:
            return None

        return Status(
            state=BITBUCKET_STATUS_STATE_TO_PULLAPPROVE_STATUS_STATE[status["state"]],
            description=status["description"],
            groups=[],  # unknown... but we could potentially parse back off URL...
            report_url=status["url"],
        )

    def send_status(self, status: Status, output_data: Dict[str, Any]) -> Optional[str]:
        data = {
            "key": BITBUCKET_STATUS_KEY,
            "state": PULLAPPROVE_STATUS_STATE_TO_BITBUCKET_STATUS_STATE[status.state],
            "description": status.description[:140],
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
        data["url"] = report_url

        self.repo.api.post(
            f"/commit/{self.data['source']['commit']['hash']}/statuses/build", json=data
        )

        return report_url

    @cached_property
    def comments(self) -> List[Dict[str, Any]]:
        return self.repo.api.get(
            self.data["links"]["comments"]["href"], page_items_key="values"
        )

    @cached_property
    def commits(self) -> List[Dict[str, Any]]:
        return self.repo.api.get(
            self.data["links"]["commits"]["href"], page_items_key="values"
        )

    @cached_property
    def diffstat(self) -> List[Dict[str, Any]]:
        return self.repo.api.get(
            self.data["links"]["diffstat"]["href"], page_items_key="values"
        )

    @cached_property
    def statuses(self) -> List[Dict[str, Any]]:
        return self.repo.api.get(
            self.data["links"]["statuses"]["href"], page_items_key="values"
        )

    @cached_property
    def diff(self) -> List[Dict[str, Any]]:
        return self.repo.api.get(self.data["links"]["diff"]["href"], parse_json=False)

    def create_comment(self, body: str, ignore_mode: bool = False) -> None:
        self.repo.api.post(
            self.data["links"]["comments"]["href"],
            json={"content": {"raw": body}},
            ignore_mode=ignore_mode,
        )

    def create_or_update_comment(self, body: str, comment_id: str) -> None:
        # Not supported yet without <!-- --> comments in markdown
        self.create_comment(body)
