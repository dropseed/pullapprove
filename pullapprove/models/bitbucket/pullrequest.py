import os
import random
import time
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, quote, urlparse

from cached_property import cached_property
from pullapprove.context.bitbucket import PullRequest as PullRequestContext
from pullapprove.storage import Storage

import pullapprove.context.functions
from pullapprove.exceptions import UserError
from pullapprove.logger import canonical, logger
from pullapprove.models.base import BasePullRequest
from pullapprove.settings import settings

from ..reviews import Review, Reviewers
from ..states import ReviewState, State
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
        reviewers = set([x["nickname"] for x in self.data["reviewers"]])
        updated_reviewers = reviewers | set(users_to_add)
        updated_reviewers = reviewers - set(users_to_remove)  # remove last

        if set(updated_reviewers) == reviewers:
            return

        # going to have to use nicknames in yaml
        # get list of workspaces/name/members
        # convert nicknames to uuids, use those here
        # - so the caveat is that nicknames should be unique in your workspace... and you don't want to change them...
        members_by_nickname = {
            x["user"]["nickname"]: x for x in self.repo.workspace_members  # type: ignore
        }

        reviewers_json = []

        for nickname in updated_reviewers:
            try:
                reviewers_json.append(
                    {"uuid": members_by_nickname[nickname]["user"]["uuid"]}
                )
            except KeyError:
                raise UserError(f'UUID not found for user "{nickname}"')

        self.repo.api.put(
            f"/pullrequests/{self.number}",
            json={
                "reviewers": reviewers_json,
                # Has to have the title field to be valid...
                "title": self.data["title"],
            },
        )

    def get_current_status(self) -> Dict[str, Any]:
        statuses = self.repo.api.get(
            self.data["links"]["statuses"]["href"],
            page_items_key="values",
        )

        for status in statuses:
            if status["key"] == BITBUCKET_STATUS_KEY:
                # TODO need to map back though to states we recognize?
                # this latest_status in base pull_request
                return status

        return {}

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
        # TODO should_send_status

        report_url = self.store_report(output_data)

        data = {
            "key": BITBUCKET_STATUS_KEY,
            "state": PULLAPPROVE_STATUS_STATE_TO_BITBUCKET_STATUS_STATE[status.state],
            "description": status.description[:140],
            "url": report_url,
        }

        self.repo.api.post(
            f"/commit/{self.data['source']['commit']['hash']}/statuses/build", json=data
        )
        # data = {
        #     "title": "PullApprove",
        #     "details": status.description,
        #     "report_type": "SECURITY",
        #     "result": bitbucket_states[status.state],
        #     "link": report_url or "https://www.pullapprove.com",
        #     "data": [
        #         {"title": group.name, "type": "TEXT", "value": group.state}
        #         for group in status.groups
        #         if group.is_active
        #     ],
        # }

        # self.repo.api.put(
        #     f"/commit/{self.data['source']['commit']['hash']}/reports/pullapprove",
        #     json=data,
        # )

        return report_url
