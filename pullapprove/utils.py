import datetime
import hashlib
import json
from typing import Any, Dict


def _datetime_parser(dict_: Dict) -> Dict:
    for k, v in dict_.items():
        if isinstance(v, str) and v.endswith("Z"):
            try:
                dict_[k] = datetime.datetime.strptime(v, "%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                pass
        elif isinstance(v, str) and v.endswith("+00:00"):
            try:
                dict_[k] = datetime.datetime.fromisoformat(v)
            except Exception:
                pass
    return dict_


def json_load(text: str) -> Dict:
    return json.loads(text, object_hook=_datetime_parser)


def fingerprint_for_data(data: Any) -> str:
    return hashlib.md5(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()
