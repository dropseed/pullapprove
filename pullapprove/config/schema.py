import collections
import json
import os
from typing import Any, Callable, Dict, Optional, Tuple
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

    def deserialize(self, value, attr=None, data=None, **kwargs):
        self._validate_missing(value)
        if value is missing_:
            _miss = self.missing
            value = _miss() if callable(_miss) else _miss
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
    extends = fields.String(missing="")

    @pre_load
    def extend(self, data, **kwargs):
        if not data:
            return data

        extends = data.get("extends", "")
        if not extends:
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
                if isinstance(keep[k], collections.Mapping) and isinstance(
                    add[k], collections.Mapping
                ):
                    copied = keep[k].copy()
                    ret[k] = self._dict_deep_merge(copied, add[k].copy())

        return ret


class ReviewersSchema(Schema):
    teams = fields.List(fields.Str(), missing=[])
    users = fields.List(fields.Str(), missing=[])


class ReviewsSchema(Schema):
    required = fields.Integer(default=1, missing=1)
    request = fields.Integer(default=1, missing=1)
    request_order = fields.String(
        default="random", missing="random"
    )  # should be choices
    author_value = fields.Integer(default=0, missing=0)
    reviewed_for = fields.String(
        default="optional",
        missing="optional",
        validate=validate.OneOf(["required", "optional", "ignored"]),
    )

    @pre_load
    def request_default_required(self, data, **kwargs):
        if "required" in data and "request" not in data:
            data["request"] = data["required"]

        return data


class LabelsSchema(Schema):
    approved = fields.String(missing="")
    pending = fields.String(missing="")
    rejected = fields.String(missing="")


class NotificationSchema(Schema):
    when = fields.String(required=True)
    comment = fields.String(required=True)
    comment_behavior = fields.String(
        default="create",
        missing="create",
        validate=validate.OneOf(["create", "create_or_update"]),
    )

    class Meta:
        # "if" is a Python keyword
        include = {
            "if": fields.String(missing=""),
        }


class GroupSchema(Schema):
    meta = fields.Raw(default=None, missing=None)
    description = fields.String(missing="")
    type = fields.String(
        default="required",
        missing="required",
        validate=validate.OneOf(["required", "optional"]),
    )
    conditions = fields.List(fields.Str(), missing=[])
    requirements = fields.List(fields.Str(), missing=[])
    reviewers = Nested(ReviewersSchema(), missing={})
    reviews = Nested(ReviewsSchema(), missing={})
    labels = Nested(LabelsSchema(), missing={})


class PullApproveConditionSchema(Schema):
    condition = fields.String(required=True)
    unmet_status = fields.String(
        default="success",
        missing="success",
        validate=validate.OneOf(["success", "pending", "failure"]),
    )
    explanation = fields.String(missing="")

    @pre_load
    def convert_str_type(self, data, **kwargs):
        if isinstance(data, str):
            return {"condition": data}

        return data


class OverridesSchema(Schema):
    status = fields.String(
        required=True,
        validate=validate.OneOf(["success", "pending", "failure"]),
    )
    explanation = fields.String(missing="")

    class Meta:
        # "if" is a Python keyword
        include = {
            "if": fields.String(required=True),
        }


class AvailabilitySchema(ExtendableSchema):
    users_unavailable = fields.List(fields.Str(), missing=[])


class ConfigSchema(ExtendableSchema):
    version = fields.Integer(required=True, validate=validate.OneOf([3]))
    meta = fields.Raw(default=None, missing=None)
    github_api_version = fields.String(missing="")
    groups = fields.Mapping(
        keys=fields.String(),
        values=Nested(GroupSchema()),
        missing={},
    )
    pullapprove_conditions = fields.List(
        Nested(PullApproveConditionSchema()), missing=[]
    )
    overrides = fields.List(Nested(OverridesSchema()), missing=[])
    notifications = fields.List(Nested(NotificationSchema()), missing=[])
    availability = Nested(AvailabilitySchema(), missing={})


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
