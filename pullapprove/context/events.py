from typing import Any, Dict, Type

from .base import ContextObject


class BaseEvent(ContextObject):
    _eq_attr = "name"
    _contains_attr = "name"
    _subtypes: Dict[str, Type[ContextObject]] = {
        # Should include pullapprove event fields in subclass
        # "requested_reviewers": Accounts,
        # "unrequested_reviewers": Accounts,
        # "group": groups.Group,
    }

    def __init__(self, name: str, *args: Any, **kwargs: Any) -> None:
        self.name = name
        super().__init__(*args, **kwargs)
