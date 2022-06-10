from typing import Any, Dict, List, Optional

from cached_property import cached_property

import pullapprove.context.functions
import pullapprove.user_input.template
from pullapprove.context.gitlab import MergeRequest as MergeRequestContext
from pullapprove.models.base import BasePullRequest
from pullapprove.models.reviews import Review, Reviewers, ReviewState
from pullapprove.models.status import Status
from pullapprove.settings import settings

from .states import (
    GITLAB_STATUS_STATE_TO_PULLAPPROVE_STATUS_STATE,
    PULLAPPROVE_STATUS_STATE_TO_GITLAB_STATUS_STATE,
)

GITLAB_STATUS_NAME = settings.get("GITLAB_STATUS_NAME", "pullapprove")


class MergeRequest(BasePullRequest):
    def as_context(self) -> Dict[str, Any]:
        merge_request = MergeRequestContext(self)
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

    @property
    def latest_sha(self) -> str:
        return self.data["sha"]

    @cached_property
    def _approvals(self) -> Dict[str, Any]:
        return self.repo.api.get(
            f"/merge_requests/{self.number}/approvals",
            headers={"Cache-Control": "max-age=1, min-fresh=1"},
        )

    @cached_property
    def diffs(self) -> List[Dict[str, Any]]:
        return self.repo.api.get(
            f"/repository/commits/{self.data['diff_refs']['head_sha']}/diff"
        )

    @property
    def reviewers(self) -> Reviewers:
        reviewers = Reviewers()

        for user in self.data["reviewers"]:
            review = Review(state=ReviewState.PENDING, body="")
            reviewers.append_review(username=user["username"], review=review)

        # make sure approved overwrites anybody pending in another group...
        # not sure if this will actually happen
        for user in self._approvals["approved_by"]:
            review = Review(state=ReviewState.APPROVED, body="")
            reviewers.append_review(username=user["username"], review=review)

        return reviewers

    @property
    def users_requested(self) -> List[str]:
        return [x["username"] for x in self.data["reviewers"]]

    def set_labels(
        self, labels_to_add: List[str], labels_to_remove: List[str]
    ) -> List[str]:
        current_labels = set(self.data["labels"])

        # labels are removed, THEN added so that if there are duplicates across groups,
        # they end up being added if they are supposed to be present
        updated_labels = current_labels - set(labels_to_remove)
        updated_labels = updated_labels | set(labels_to_add)

        if updated_labels != current_labels:
            self.repo.api.put(
                f"/merge_requests/{self.number}",
                json={"labels": ",".join(updated_labels)},
            )

        return list(updated_labels)

    def set_reviewers(
        self, users_to_add: List[str], users_to_remove: List[str], total_required: int
    ) -> None:
        existing_reviewer_ids = [x["id"] for x in self.data["reviewers"]]

        project_users = self.repo.api.get("/users")
        add_user_ids = [x["id"] for x in project_users if x["username"] in users_to_add]
        remove_user_ids = [
            x["id"] for x in project_users if x["username"] in users_to_remove
        ]

        updated_reviewer_ids = list(
            set(existing_reviewer_ids) | set(add_user_ids) - set(remove_user_ids)
        )

        if not existing_reviewer_ids and not updated_reviewer_ids:
            # Nothing to change, don't waste a call to the API
            return

        if existing_reviewer_ids != updated_reviewer_ids:
            self.repo.api.put(
                f"/merge_requests/{self.number}",
                json={"reviewer_ids": updated_reviewer_ids},
            )

    # def set_reviewers(
    #     self, users_to_add: List[str], users_to_remove: List[str], total_required: int
    # ) -> None:

    #     # seems like you can only have 1 custom rule?
    #     # TODO is this different in premium self-hosted?
    #     # and rule must exist already, I think

    #     existing_rule = [
    #         x
    #         for x in self._approval_state["rules"]
    #         if x["name"].lower() == GITLAB_APPROVAL_RULE_NAME.lower()
    #     ]

    #     if existing_rule:
    #         updated_users = list(
    #             set(x["username"] for x in existing_rule[0]["users"])  # type: ignore
    #             | set(users_to_add) - set(users_to_remove)
    #         )
    #     else:
    #         updated_users = list(set(users_to_add) - set(users_to_remove))

    #     if not updated_users:
    #         # Can't make an approval rule with no users
    #         # clashes with built-in any-approver rule
    #         return

    #     # could potentially save on this if the needed users are already in the rule.users
    #     project_users = self.repo.api.get("/users")
    #     updated_users_ids = [
    #         x["id"] for x in project_users if x["username"] in updated_users
    #     ]

    #     if len(updated_users_ids) != len(updated_users):
    #         raise Exception("Unable to find ID for some users")

    #     rule_data = {
    #         "approvals_required": total_required,
    #         "user_ids": updated_users_ids,
    #     }

    #     if existing_rule:
    #         rule_id = existing_rule[0]["id"]  # type: ignore
    #         self.repo.api.put(
    #             f"/merge_requests/{self.number}/approval_rules/{rule_id}",
    #             json=rule_data,
    #             user_error_status_codes={
    #                 403: "MR approval override may not be enabled."
    #             },
    #         )
    #     else:
    #         rule_data["name"] = GITLAB_APPROVAL_RULE_NAME
    #         self.repo.api.post(
    #             f"/merge_requests/{self.number}/approval_rules",
    #             json=rule_data,
    #             # user_error_status_codes={403: "MR approval override may not be enabled."},
    #         )

    # def create_comment(self, body, ignore_mode=False) -> None:
    #     self.repo.api.post(
    #         f"/merge_requests/{self.number}/notes",
    #         json={"body": body},
    #         ignore_mode=ignore_mode,
    #     )

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
            "state": PULLAPPROVE_STATUS_STATE_TO_GITLAB_STATUS_STATE[status.state],
            "ref": self.data["source_branch"],
            "description": status.description[:140],
            "target_url": None,
            "name": GITLAB_STATUS_NAME,
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

        # if report_url and len(report_url) >= 255:
        #     report_url = utils.shorten_report_url(report_url)

        if report_url:
            data["target_url"] = report_url

        # Maybe gitlab does not use status at all because of the dumb pipelines...
        # so a comment is the next best? which is how I got to comment template?

        # so status/pipeline vs comment is one question
        # and reviewers vs approval rule is another - approval rule may be the only way to get requirement though
        # - whether approval rule has to already exist is the dumb question on that one

        self.repo.api.post(f"/statuses/{self.latest_sha}", json=data)

        # self._send_status_comment(status, report_url)

        return report_url

    @cached_property
    def latest_status(self) -> Optional[Status]:
        statuses = self.repo.api.get(
            f"/repository/commits/{self.latest_sha}/statuses",
            params={"name": GITLAB_STATUS_NAME},
        )
        if statuses:
            return Status(
                state=GITLAB_STATUS_STATE_TO_PULLAPPROVE_STATUS_STATE[
                    statuses[0]["status"]
                ],
                description=statuses[0]["description"],
                groups=[],
                report_url=statuses[0]["target_url"],
            )

        return None
