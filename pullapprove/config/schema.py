import collections.abc
import json
import os
from typing import Any, Callable, Dict, Mapping, Optional, Tuple
from urllib.parse import urlparse

import yaml
from box import Box
from marshmallow import Schema, ValidationError, fields
from marshmallow import missing as missing_
from marshmallow import pre_load, validate

from pullapprove.exceptions import UserError

# Every field should have "required" or "missing",
# so that we always have a fully traversable dict regardless of partial input


class Nested(fields.Nested):
    """
    Field that will fill in nested before loading so nested missing fields will be initialized
    using nested defaults/missing.
    https://github.com/marshmallow-code/marshmallow/issues/1042#issuecomment-509126100
    """

    def deserialize(
        self,
        value: Any,
        attr: Optional[str] = None,
        data: Optional[Mapping[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        self._validate_missing(value)
        if value is missing_:
            value = (
                self.load_default()
                if callable(self.load_default)
                else self.load_default
            )
        return super().deserialize(value, attr, data, **kwargs)


class ExtendsLoader:
    def __init__(
        self,
        compile_shorthand: Callable,
        get_url_response: Callable,
    ) -> None:
        self.compile_shorthand = compile_shorthand
        self.get_url_response = get_url_response

    def load(self, s: str) -> Dict[str, Any]:
        url, extend_field = self.parse_string(s)
        response = self.get_url_response(url)
        if not response.ok:
            raise UserError(
                f"Failed to load `extends` URL (HTTP {response.status_code})"
            )
        return self.load_url_data(
            url=url,
            text=response.text,
            field_key=extend_field,
        )

    def parse_string(self, s: str) -> Tuple[str, str]:
        if s.startswith("./"):
            s, extend_field = self._split_last(s, "#")
            filename = s[2:]  # remove leading ./
            url = self.compile_shorthand(filename=filename)
        elif s.startswith("https://"):
            s, extend_field = self._split_last(s, "#")
            url = s
        else:
            # Shorthand:
            # owner/repo@354354:.pullapprove.yml#groups.code
            s, extend_field = self._split_last(s, "#")
            s, extend_filename = self._split_last(s, ":")
            s, extend_ref = self._split_last(s, "@")
            extend_repo = s
            url = self.compile_shorthand(
                repo=extend_repo, filename=extend_filename, ref=extend_ref
            )

        if urlparse(url).scheme != "https":
            raise UserError("Template URL must be https")

        return url, extend_field

    def load_url_data(self, url: str, text: str, field_key: str) -> Any:
        extension = os.path.splitext(urlparse(url).path)[1]

        if extension in (".yml", ".yaml"):
            try:
                extend_data = yaml.safe_load(text)
            except yaml.YAMLError:
                raise UserError('Error decoding YAML from "extends"')
        else:
            # Default is JSON
            try:
                extend_data = json.loads(text)
            except json.JSONDecodeError:
                raise UserError('Error decoding JSON from "extends"')

        if field_key:
            extend_data = self._get_dict_part_by_dotstr(extend_data, field_key)

        return extend_data

    def _split_last(self, s: str, delimiter: str) -> Tuple[str, str]:
        parts = s.split(delimiter)
        if len(parts) > 1:
            return delimiter.join(parts[:-1]), parts[-1]

        return s, ""

    def _get_dict_part_by_dotstr(self, data: Dict[str, Any], dotstr: str) -> Any:
        box = Box(data, box_dots=True)
        part = box[dotstr]
        return part


class ExtendableSchema(Schema):
    extends = fields.String(load_default="")

    @pre_load
    def extend(self, data: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        if not data:
            return data

        extends = data.get("extends", "")
        if not extends or not isinstance(extends, str):
            return data

        load_extends_func = self.context["load_extends_func"]

        extended_data = load_extends_func(extends)

        if "extends" in extended_data:
            raise ValidationError('Extended config can\'t also use "extends"')

        return self._dict_deep_merge(extended_data, data)

    def _dict_deep_merge(self, keep: dict, add: dict) -> dict:
        """NOTE: this does not update keep itself, it returns a new dict"""
        ret = keep.copy()

        # do the basic update, overwriting everything
        ret.update(add)

        # now go back through and see if we want to deal with any types differently
        for k, v in ret.items():
            # if both dicts had this key
            if k in keep and k in add:
                # if both of those values were dicts, decide how we want to merge them
                if isinstance(keep[k], collections.abc.Mapping) and isinstance(
                    add[k], collections.abc.Mapping
                ):
                    copied = keep[k].copy()
                    ret[k] = self._dict_deep_merge(copied, add[k].copy())

        return ret


class ReviewersSchema(Schema):
    teams = fields.List(fields.Str(), load_default=[])
    users = fields.List(fields.Str(), load_default=[])


class ReviewsSchema(Schema):
    required = fields.Integer(dump_default=1, load_default=1)
    request = fields.Integer(dump_default=1, load_default=1)
    request_order = fields.String(
        dump_default="random", load_default="random"
    )  # should be choices
    author_value = fields.Integer(dump_default=0, load_default=0)
    reviewed_for = fields.String(
        dump_default="optional",
        load_default="optional",
        validate=validate.OneOf(["required", "optional", "ignored"]),
    )

    @pre_load
    def request_default_required(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> Dict[str, Any]:
        if "required" in data and "request" not in data:
            data["request"] = data["required"]

        return data


class LabelsSchema(Schema):
    approved = fields.String(load_default="")
    pending = fields.String(load_default="")
    rejected = fields.String(load_default="")


class NotificationSchema(Schema):
    when = fields.String(required=True)
    comment = fields.String(required=True)
    comment_behavior = fields.String(
        dump_default="create",
        load_default="create",
        validate=validate.OneOf(["create", "create_or_update"]),
    )

    class Meta:
        # "if" is a Python keyword
        include = {
            "if": fields.String(load_default=""),
        }


class GroupSchema(Schema):
    meta = fields.Raw(dump_default=None, load_default=None)
    description = fields.String(load_default="")
    type = fields.String(
        dump_default="required",
        load_default="required",
        validate=validate.OneOf(["required", "optional"]),
    )
    conditions = fields.List(fields.Str(), load_default=[])
    requirements = fields.List(fields.Str(), load_default=[])
    reviewers = Nested(ReviewersSchema(), load_default={})
    reviews = Nested(ReviewsSchema(), load_default={})
    labels = Nested(LabelsSchema(), load_default={})


class PullApproveConditionSchema(Schema):
    condition = fields.String(required=True)
    unmet_status = fields.String(
        dump_default="success",
        load_default="success",
        validate=validate.OneOf(["success", "pending", "failure"]),
    )
    explanation = fields.String(load_default="")

    @pre_load
    def convert_str_type(self, data: Any, **kwargs: Any) -> Any:
        if isinstance(data, str):
            return {"condition": data}

        return data


class OverridesSchema(Schema):
    status = fields.String(
        required=True,
        validate=validate.OneOf(["success", "pending", "failure"]),
    )
    explanation = fields.String(load_default="")

    class Meta:
        # "if" is a Python keyword
        include = {
            "if": fields.String(required=True),
        }


class AvailabilitySchema(ExtendableSchema):
    users_unavailable = fields.List(fields.Str(), load_default=[])


class ConfigSchema(ExtendableSchema):
    version = fields.Integer(required=True, validate=validate.OneOf([3]))
    meta = fields.Raw(dump_default=None, load_default=None)
    github_api_version = fields.String(load_default="")
    groups = fields.Mapping(
        keys=fields.String(),
        values=Nested(GroupSchema()),
        load_default={},
    )
    pullapprove_conditions = fields.List(
        Nested(PullApproveConditionSchema()), load_default=[]
    )
    overrides = fields.List(Nested(OverridesSchema()), load_default=[])
    notifications = fields.List(Nested(NotificationSchema()), load_default=[])
    availability = Nested(AvailabilitySchema(), load_default={})


class Config:
    def __init__(self, text: str, load_extends_func: Optional[Callable] = None) -> None:
        self.original_text = text
        self.validation_error = None
        self.schema = ConfigSchema()
        self.data = {}

        try:
            self.original_data = yaml.safe_load(self.original_text)
        except yaml.YAMLError as e:
            raise UserError("Error loading YAML. Check the formatting.")

        if load_extends_func:
            self.schema.context["load_extends_func"] = load_extends_func

        try:
            self.data = self.schema.load(self.original_data)
        except ValidationError as e:
            self.validation_error = e

    def is_valid(self) -> bool:
        return not bool(self.validation_error)

    def as_dict(self) -> Dict[str, Any]:
        output = {
            "config_text": self.original_text,
            "config": self.data,
        }

        if self.validation_error:
            output["errors"] = [str(self.validation_error)]

        return output
