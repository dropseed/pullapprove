import re
from typing import Iterator, List, Optional

from .states import ReviewState


class Review:
    def __init__(self, state: str, body: str) -> None:
        self.state = state
        self.body = body

    def is_for(self, name: str, behavior: str) -> bool:
        if behavior == "ignored":
            return True

        must_be_explicit = behavior == "required"

        matches = re.findall(
            "^Reviewed-for:(.+)$", self.body, (re.MULTILINE | re.IGNORECASE)
        )

        # Nothing was specified, and nothing had to be
        if not matches and not must_be_explicit:
            return True

        for match_string in matches:
            group_names = [x.strip().lower() for x in match_string.split(",")]
            if name.lower() in group_names:
                return True

        return False


class Reviewer:
    def __init__(self, username: str) -> None:
        self.username = username
        self.reviews: List[Review] = []

    def approved_for(self, name: str, behavior: str) -> bool:
        return self._state_for(name, behavior=behavior) == ReviewState.APPROVED

    def rejected_for(self, name: str, behavior: str) -> bool:
        return self._state_for(name, behavior=behavior) == ReviewState.REJECTED

    def pending_for(self, name: str, behavior: str) -> bool:
        return self._state_for(name, behavior=behavior) == ReviewState.PENDING

    def _state_for(self, name: str, behavior: str) -> Optional[str]:
        state = None
        for review in self.reviews:
            if review.is_for(name, behavior=behavior):
                state = review.state
        return state


class Reviewers:
    def __init__(self) -> None:
        self._reviewers: List[Reviewer] = []

    def append_review(self, username, review):
        try:
            reviewer = [x for x in self._reviewers if x.username == username][0]
        except IndexError:
            reviewer = Reviewer(username)
            self._reviewers.append(reviewer)

        reviewer.reviews.append(review)

    def approved_for(self, name: str, behavior: str) -> List[Reviewer]:
        return [x for x in self._reviewers if x.approved_for(name, behavior=behavior)]

    def rejected_for(self, name: str, behavior: str) -> List[Reviewer]:
        return [x for x in self._reviewers if x.rejected_for(name, behavior=behavior)]

    def pending_for(self, name: str, behavior: str) -> List[Reviewer]:
        return [x for x in self._reviewers if x.pending_for(name, behavior=behavior)]

    def __len__(self) -> int:
        return len(self._reviewers)

    def __getitem__(self, key):
        return self._reviewers[key]

    def __iter__(self) -> Iterator[Reviewer]:
        return iter(self._reviewers)
