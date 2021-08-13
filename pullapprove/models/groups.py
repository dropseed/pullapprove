from random import Random, shuffle
from typing import TYPE_CHECKING, Any, Dict, List, Set

from pullapprove.context.groups import Group as GroupContext, Groups as GroupsContext

from . import expressions
from .states import ReviewState

if TYPE_CHECKING:
    from .base.pull_request import BasePullRequest


class Group:
    @classmethod
    def from_config(cls, name: str, config_schema: Dict[str, Any]) -> "Group":
        obj = cls(name)  # type: ignore

        obj.users = config_schema["reviewers"]["users"]
        obj.teams = config_schema["reviewers"]["teams"]
        obj.required = config_schema["reviews"]["required"]
        obj.request = config_schema["reviews"]["request"]
        obj.request_order = config_schema["reviews"]["request_order"]
        obj.author_value = config_schema["reviews"]["author_value"]
        obj.reviewed_for = config_schema["reviews"]["reviewed_for"]
        obj.labels = config_schema["labels"]
        obj.description = config_schema["description"]
        obj.type = config_schema["type"]
        obj.conditions = [
            expressions.Expression(x) for x in config_schema["conditions"]
        ]
        obj.requirements = [
            expressions.Expression(x) for x in config_schema["requirements"]
        ]

        return obj

    def __init__(self, name: str) -> None:
        self.name = name
        self.state = ReviewState.PENDING
        self.users: List[str] = []
        self.teams: List[str] = []
        self.conditions: List[expressions.Expression] = []
        self.requirements: List[expressions.Expression] = []
        self.labels: Dict[str, str] = {}
        self.required = 1
        self.score = 0
        self.bonus = 0
        self.request = 1
        self.request_order = "random"
        self.author_value = 0
        self.reviewed_for = "optional"
        self.description = ""
        self.type = "required"

        self.users_approved: List[str] = []
        self.users_rejected: List[str] = []
        self.users_pending: List[str] = []
        self.users_unavailable: List[str] = []
        self.users_available: List[str] = []
        self.users_to_request: List[str] = []
        self.users_to_unrequest: List[str] = []

    @property
    def is_active(self) -> bool:
        return all([x.is_met for x in self.conditions])

    @property
    def meets_requirements(self) -> bool:
        return all([x.is_met for x in self.requirements])

    @property
    def is_passing(self) -> bool:
        if not self.is_active:
            return True

        return self.state == ReviewState.APPROVED

    @property
    def is_required(self) -> bool:
        return self.type == "required"

    def load_pr(
        self,
        pr: "BasePullRequest",
        other_groups: List[Dict],
        users_already_unavailable: List[str],
        users_already_requested: List[str],
    ) -> None:
        self.load_conditions(pr, other_groups)

        users_unrequestable: Set[str] = set()

        # needs to maintain order, so needs to be a list
        users_in_group = [without_prefixes(x) for x in self.users]
        for team in self.teams:
            usernames = pr.repo.get_usernames_in_team(without_prefixes(team))
            new_usernames = [x for x in usernames if x not in users_in_group]
            users_in_group += new_usernames

            # these users don't want review requests
            if is_unrequestable(team):
                users_unrequestable.update(usernames)

        # process unrequestable users after teams because they are more specific
        for user in self.users:
            if is_unrequestable(user):
                users_unrequestable.add(without_prefixes(user))
            elif without_prefixes(user) in users_unrequestable:
                users_unrequestable.remove(without_prefixes(user))

        # teams and users not used after this point

        # if the group hasn't defined anybody,
        # then these are the values we'll use
        users_approved: Set[str] = set(
            x.username
            for x in pr.reviewers.approved_for(self.name, behavior=self.reviewed_for)
        )
        users_rejected: Set[str] = set(
            x.username
            for x in pr.reviewers.rejected_for(self.name, behavior=self.reviewed_for)
        )
        users_pending: Set[str] = set(
            [
                x.username
                for x in pr.reviewers.pending_for(self.name, behavior=self.reviewed_for)
            ]
            + pr.users_requested
            + users_already_requested
            + list(users_rejected)  # rejected, but still involved for future approval
        )
        users_unavailable: Set[str] = set(users_already_unavailable)
        users_to_unrequest: Set[str] = set()

        if users_in_group:
            users_in_group_set = set(users_in_group)
            users_approved = users_in_group_set.intersection(users_approved)
            users_rejected = users_in_group_set.intersection(users_rejected)
            users_pending = users_in_group_set.intersection(users_pending)
            users_unavailable = users_in_group_set.intersection(users_unavailable)
            users_to_unrequest = users_unavailable.intersection(users_pending)

            # we'll keep these users in "unavailable", but won't actually remove any review requests
            # in case someone wants to tag them manually
            users_unavailable = users_unavailable.union(users_unrequestable)

        # make sure these are lists, not sets
        self.users_approved = list(users_approved)
        self.users_rejected = list(users_rejected)
        self.users_pending = list(users_pending)
        self.users_unavailable = list(users_unavailable)
        self.users_to_unrequest = list(users_to_unrequest)

        # this needs to maintain order again
        self.users_available = [
            x
            for x in users_in_group
            if x
            not in (users_approved | users_rejected | users_pending | users_unavailable)
        ]

        self.state = ReviewState.PENDING

        self.score = len(self.users_approved)

        # Determine bonuses
        if pr.author in users_in_group:
            # in gitlab, author could technically still review and add an additional point for their approval
            # so these are "auto points"
            self.bonus = self.bonus + self.author_value

        self.score = self.score + self.bonus

        if self.score >= self.required:
            self.state = ReviewState.APPROVED

        if self.required < 0 and (self.users_pending or self.users_available):
            # -1 means everybody has to review
            self.state = ReviewState.PENDING

        # even a single rejection means rejection (same as GH rules)
        if self.users_rejected:
            self.state = ReviewState.REJECTED

        # get the users who should be requested, and then put them in the correct
        # categories for their future state (move who will be requested and unrequested)
        self.users_to_request = self.get_users_to_request(pr_number=pr.number)
        self.users_available = [
            x for x in self.users_available if x not in self.users_to_request
        ]
        self.users_pending += self.users_to_request

        self.load_requirements(pr, other_groups)

        if not self.meets_requirements:
            self.state = ReviewState.PENDING

    def load_conditions(self, pr: "BasePullRequest", groups: List[Dict[str, Any]]):
        ctx = pr.as_context()
        ctx["groups"] = GroupsContext(groups)

        for condition in self.conditions:
            condition.load(ctx)

    def load_requirements(self, pr: "BasePullRequest", groups: List[Dict[str, Any]]):
        ctx = pr.as_context()
        ctx["groups"] = GroupsContext(groups)

        group_data = self.as_dict()
        group_data.pop("requirements")  # not loaded yet
        group_data.pop("is_passing")  # depends on requirements
        group_data.pop("is_active")  # not useful - requirements only run when is_active
        ctx["group"] = GroupContext(group_data)

        for requirement in self.requirements:
            requirement.load(ctx)

    def get_users_to_request(self, pr_number: int) -> List[str]:
        if self.is_passing:
            return []

        if self.request == 0:
            return []

        if self.required > 0 and self.score >= self.required:
            return []

        users_requestable = self.users_available
        if self.request_order.lower().strip() in ("shuffle", "random"):
            # by sorting and then using a manual random seed, we should
            # get consistent shuffle results even in race conditions (seed will be PR number)
            #
            # sort it BEFORE the shuffle, not inside (shuffle in place won't work otherwise)
            users_requestable = sorted(users_requestable)
            Random(pr_number).shuffle(users_requestable)
        # elif self.request_order.lower().strip() == "round_robin":
        #     # use existing order - users is explicit, and teams *should* have an
        #     # order from the API already
        #     users_requestable = rotate_list_left(users_requestable, pr_number)

        if self.request < 0:
            # true for all scenarios:
            # - self.required < 0
            # - self.required == 0
            # - self.required > 0
            return users_requestable

        # need everybody, but should only have X pending at a time
        if self.required < 0 and self.request > 0:
            still_could_send = self.request - len(self.users_pending)
            if still_could_send > 0:
                return users_requestable[:still_could_send]

        if self.required == 0 and self.request > 0:
            still_could_send = self.request - len(self.users_pending) - self.score
            if still_could_send > 0:
                return users_requestable[:still_could_send]

        # only need a fixed amount, and can only send X at a time
        if self.required > 0 and self.request > 0:
            if self.request > self.required:
                # current approvals are irrelevant (unless already passing above)
                # so we should have X pending at all times
                still_could_send = self.request - len(self.users_pending)
                if still_could_send > 0:
                    return users_requestable[:still_could_send]

            else:
                # need X many more to possibly meet requirement
                still_could_send = self.required - len(self.users_pending) - self.score
                # limited by request
                still_could_send = min(still_could_send, self.request)
                if still_could_send > 0:
                    return users_requestable[:still_could_send]

        return []

    def as_dict(self) -> Dict[str, Any]:
        # str lists need to be sorted for later fingerprinting consistency
        return {
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "is_active": self.is_active,
            "is_passing": self.is_passing,
            "state": self.state,
            "required": self.required,
            "score": self.score,
            "request": self.request,
            "request_order": self.request_order,
            "author_value": self.author_value,
            "reviewed_for": self.reviewed_for,
            "conditions": [x.as_dict() for x in self.conditions],
            "requirements": [x.as_dict() for x in self.requirements],
            "labels": self.labels,
            "users": sorted(self.users),
            "teams": sorted(self.teams),
            "users_approved": sorted(self.users_approved),
            "users_rejected": sorted(self.users_rejected),
            "users_pending": sorted(self.users_pending),
            "users_unavailable": sorted(self.users_unavailable),
            "users_available": sorted(self.users_available),
            "users_requested": sorted(self.users_to_request),
            "users_unrequested": sorted(self.users_to_unrequest),
        }


def without_prefixes(name: str) -> str:
    # other prefiex can be used here too
    return name.lstrip("~")


def is_unrequestable(name: str) -> bool:
    return name.startswith("~")


def rotate_list_left(l, num):
    rotate_by = num % len(l)
    return l[rotate_by:] + l[:rotate_by]
