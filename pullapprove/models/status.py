from typing import TYPE_CHECKING, Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from .states import ReviewState, State

if TYPE_CHECKING:
    from .groups import Group


class Status:
    def __init__(
        self,
        state: str,
        description: str = "",
        groups: List["Group"] = [],
        report_url: str = "",
    ) -> None:
        self.state = state
        self.description = description
        self.groups = groups
        self.report_url = report_url

    @classmethod
    def from_groups(cls, groups: List["Group"]) -> "Status":
        return cls(
            state=state_from_groups(groups),
            description=description_from_groups(groups),
            groups=groups,
        )

    def __str__(self) -> str:
        return f"{self.state} - {self.description}"

    @property
    def report_fingerprint(self) -> str:
        if not self.report_url:
            return ""

        query_params = parse_qs(urlparse(self.report_url).query)
        fingerprint = query_params.get("fingerprint", [""])[
            0
        ]  # query params has a list

        return fingerprint

    def is_the_same_as(
        self,
        state: Optional[str],
        description: Optional[str],
        fingerprint: Optional[str],
    ) -> bool:
        if self.report_url:
            # TODO HEAD request on target_url to make sure still exists?
            return self.report_fingerprint == fingerprint

        # Fallback to a basic comparision if we don't have a URL (we will typically have a URL)
        return self.state == state and self.description == description

    def is_approved(self) -> bool:
        """Have all of the active required groups passed, and was there at least 1 active required group?"""
        if self.state != State.SUCCESS:
            return False

        return any([x.is_active and x.is_required for x in self.groups]) and all(
            [x.is_passing for x in self.groups if x.is_required]
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "explanation": self.description,  # TODO deprecate and rename to description
            "groups": {x.name: x.as_dict() for x in self.groups},
        }


def description_from_groups(groups: List["Group"]) -> str:
    active_required_groups = [x for x in groups if x.is_active and x.is_required]

    if not active_required_groups:
        return "No review groups are required"

    states = (ReviewState.REJECTED, ReviewState.PENDING, ReviewState.APPROVED)

    explanation_parts = []

    for state in states:
        filtered = [x for x in active_required_groups if x.state == state]
        if filtered:
            plural = "s" if len(filtered) > 1 else ""
            explanation_parts.append(f"{len(filtered)} group{plural} {state}")

    explanation = ", ".join(explanation_parts)
    return explanation


def state_from_groups(groups: List["Group"]) -> str:
    for group in groups:
        if (
            group.is_active
            and group.is_required
            and group.state == ReviewState.REJECTED
        ):
            # Any rejection is a failure
            return State.FAILURE

        if (
            group.is_active
            and group.is_required
            and group.state != ReviewState.APPROVED
        ):
            return State.PENDING

    return State.SUCCESS
