import os
import re
from typing import Any, Dict, List, Optional

from cached_property import cached_property

import pullapprove.context.functions
import pullapprove.context.gitlab
import pullapprove.user_input.template
from pullapprove.exceptions import UserError
from pullapprove.logger import canonical, logger
from pullapprove.models.base import BasePullRequest
from pullapprove.models.reviews import Review, Reviewers, ReviewState
from pullapprove.models.states import State
from pullapprove.models.status import Status
from pullapprove.settings import settings

from . import utils

GITLAB_STATUS_NAME = os.environ.get("GITLAB_STATUS_NAME", "pullapprove")
GITLAB_COMMIT_STATES = {
    State.ERROR: "failed",
    State.PENDING: "failed",
    State.SUCCESS: "success",
    State.FAILURE: "failed",
}
GITLAB_APPROVAL_RULE_NAME = os.environ.get("GITLAB_APPROVAL_RULE_NAME", "PullApprove")


class MergeRequest(BasePullRequest):
    def as_context(self) -> Dict[str, Any]:
        merge_request = pullapprove.context.gitlab.MergeRequest.from_model(self)
        return {
            **pullapprove.context.functions.get_context_dictionary(self.number),
            # make these available at the top level, not under "pullrequest.key" or something
            **{x: getattr(merge_request, x) for x in merge_request._available_keys()},
        }

    @cached_property
    def data(self) -> Dict[str, Any]:
        # TODO check event like github?
        # TODO is this actually necessary if we have event?
        headers = {"Cache-Control": "max-age=1, min-fresh=1"}
        return self.repo.api.get(f"/merge_requests/{self.number}", headers=headers)

    @property
    def base_ref(self) -> str:
        return self.data["target_branch"]

    @property
    def author(self) -> str:
        return self.data["author"]["username"]

    @cached_property
    def _approval_state(self) -> Dict[str, Any]:
        return self.repo.api.get(
            f"/merge_requests/{self.number}/approval_state",
            headers={"Cache-Control": "max-age=1, min-fresh=1"},
        )

    @property
    def reviewers(self) -> Reviewers:
        reviewers = Reviewers()

        # for rule in self._approval_state["rules"]:
        #     for user in rule["users"]:
        #         review = Review(state=ReviewState.PENDING, body="")
        #         reviewers.append_review(username=user["username"], review=review)

        # make sure approved overwrites anybody pending in another group...
        # not sure if this will actually happen
        for rule in self._approval_state["rules"]:
            for user in rule["approved_by"]:
                review = Review(state=ReviewState.APPROVED, body="")
                reviewers.append_review(username=user["username"], review=review)

        return reviewers

    @property
    def users_requested(self) -> List[str]:
        usernames = []

        for rule in self._approval_state["rules"]:
            if rule["name"].lower() == GITLAB_APPROVAL_RULE_NAME.lower():
                for user in rule["users"]:
                    usernames.append(user["username"])

        return usernames

    def set_labels(
        self, labels_to_add: List[str], labels_to_remove: List[str]
    ) -> List[str]:
        raise NotImplementedError

    def set_reviewers(
        self, users_to_add: List[str], users_to_remove: List[str], total_required: int
    ) -> None:

        # seems like you can only have 1 custom rule?
        # TODO is this different in premium self-hosted?
        # and rule must exist already, I think

        existing_rule = [
            x
            for x in self._approval_state["rules"]
            if x["name"].lower() == GITLAB_APPROVAL_RULE_NAME.lower()
        ]

        if existing_rule:
            updated_users = list(
                set(x["username"] for x in existing_rule[0]["users"])  # type: ignore
                | set(users_to_add) - set(users_to_remove)
            )
        else:
            updated_users = list(set(users_to_add) - set(users_to_remove))

        # could potentially save on this if the needed users are already in the rule.users
        project_users = self.repo.api.get("/users")
        updated_users_ids = [
            x["id"] for x in project_users if x["username"] in updated_users
        ]

        if len(updated_users_ids) != len(updated_users):
            raise Exception("Unable to find ID for some users")

        rule_data = {
            "approvals_required": total_required,
            "user_ids": updated_users_ids,
        }

        if existing_rule:
            rule_id = existing_rule[0]["id"]  # type: ignore
            self.repo.api.put(
                f"/merge_requests/{self.number}/approval_rules/{rule_id}",
                json=rule_data,
                user_error_status_codes={
                    403: "MR approval override may not be enabled."
                },
            )
        else:
            rule_data["name"] = GITLAB_APPROVAL_RULE_NAME
            self.repo.api.post(
                f"/merge_requests/{self.number}/approval_rules",
                json=rule_data,
                # user_error_status_codes={403: "MR approval override may not be enabled."},
            )

    def create_comment(self, body, ignore_mode=False) -> None:
        self.repo.api.post(
            f"/merge_requests/{self.number}/notes",
            json={"body": body},
            ignore_mode=ignore_mode,
        )

    # def _send_status_comment(self, status: Status, report_url: str) -> None:
    #     with open(
    #         os.path.join(os.path.dirname(__file__), "status_comment_template.md"), "r",
    #     ) as f:
    #         template = f.read()
    #     body = user_input.template.render(
    #         template,
    #         {
    #             # should be context like others... fns, etc.
    #             "state": status.state,
    #             "explanation": status.get_explanation(),
    #             "report_url": report_url,
    #         },
    #     )

    #     comments = self.repo.api.get(
    #         f"/merge_requests/{self.number}/notes",
    #         params={"order_by": "updated_at", "sort": "desc"},
    #         paginate=False,
    #     )
    #     comment = [
    #         x
    #         for x in comments
    #         if x["author"]["username"] == settings.get("gitlab_bot_name")
    #     ]
    #     if comment:
    #         existing_id = comment[0]["id"]
    #         # could delete and create new comment if you wanted notification? seems annoying
    #         self.repo.api.put(
    #             f"/merge_requests/{self.number}/notes/{existing_id}",
    #             json={"body": body},
    #         )
    #     else:
    #         self.create_comment(body=body)

    def send_status(self, status: Status, output_data: Dict[str, Any]) -> Optional[str]:
        data = {
            # source_project_id?
            # diff_refs.head_sha
            "state": GITLAB_COMMIT_STATES[status.state],
            "ref": self.data["source_branch"],
            "description": status.description[:140],
            "target_url": None,
            "name": GITLAB_STATUS_NAME,
        }

        if not self.should_send_status(
            data["state"], data["description"], output_data["meta"]["fingerprint"]
        ):
            return None

        report_url = self.store_report(output_data)

        if report_url and len(report_url) >= 255:
            report_url = utils.shorten_report_url(report_url)

        if report_url:
            data["target_url"] = report_url

        sha = self.data["sha"]

        # Maybe gitlab does not use status at all because of the dumb pipelines...
        # so a comment is the next best? which is how I got to comment template?

        # so status/pipeline vs comment is one question
        # and reviewers vs approval rule is another - approval rule may be the only way to get requirement though
        # - whether approval rule has to already exist is the dumb question on that one

        # self.repo.api.post(f"/statuses/{sha}", json=data)

        # self._send_status_comment(status, report_url)

        return report_url

    def should_send_status(
        self,
        state: Optional[str],
        description: Optional[str],
        fingerprint: Optional[str],
    ) -> bool:
        if not self.repo.api.mode.is_live():
            return False

        current_status = self.latest_status

        if current_status and current_status["target_url"]:
            previous_fingerprint = ""
            matches = re.findall(
                r"f(?:ingerprint)?=(\w+)", current_status["target_url"]
            )
            if matches:
                previous_fingerprint = matches[0]

            if previous_fingerprint == fingerprint:
                canonical.set(unchanged_fingerprint=True)
                logger.debug(current_status)
                return False
        elif (
            current_status
            and current_status["status"] == state
            and current_status["description"] == description
        ):
            canonical.set(unchanged_state=True)
            logger.debug(current_status)
            return False

        return True
