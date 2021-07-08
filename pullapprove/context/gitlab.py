from typing import TYPE_CHECKING, List

from .base import ContextObject, ContextObjectList

if TYPE_CHECKING:
    from pullapprove.models.gitlab.merge_request import (
        MergeRequest as MergeRequestModel,
    )


class MergeRequest(ContextObject):
    _eq_attr = "id"
    _contains_attr = "title"

    @classmethod
    def from_model(cls, merge_request_obj: "MergeRequestModel") -> "MergeRequest":
        return cls(merge_request_obj.data)

    def _available_keys(self) -> List[str]:
        keys = dir(self)
        keys += list(self._data.keys())
        keys += list(self._children.keys())
        key_set = set(keys)
        return [x for x in key_set if not x.startswith("_")]

    @property
    def number(self) -> int:
        return self.iid  # type: ignore
