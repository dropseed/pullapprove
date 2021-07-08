from . import github, groups
from .base import ContextObject


class Event(ContextObject):
    _eq_attr = "name"
    _contains_attr = "name"
    # Most of these depend on the event type, but are optional anyway
    _subtypes = {
        # pull_request - could make a type that throws an error? want to get these attrs of main obj
        "repository": github.Repo,
        "sender": github.User,
        "review": github.Review,
        "comment": github.Comment,
        "team": github.Team,
        "organization": github.User,
        # pullapprove event fields
        "group": groups.Group,
        "requested_reviewers": github.Users,
        "unrequested_reviewers": github.Users,
    }

    def __init__(self, name: str, *args, **kwargs) -> None:
        self.name = name
        super().__init__(*args, **kwargs)
