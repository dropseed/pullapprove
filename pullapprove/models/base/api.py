import os
import tempfile
from typing import Any, Callable, Dict, List

import requests
from cachecontrol import CacheControl
from cachecontrol.caches.file_cache import FileCache
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from pullapprove.exceptions import UserError
from pullapprove.logger import canonical, logger
from pullapprove.mode import Mode
from pullapprove.settings import settings
from pullapprove.utils import json_load


class BaseAPI:
    def __init__(
        self, base_url: str, headers: Dict[str, str] = {}, params: Dict[str, str] = {}
    ) -> None:
        self.base_url = base_url
        self.version = ""

        self.session = requests.Session()
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            method_whitelist=False,
            backoff_factor=2,  # only applies to the 3rd attempt (first retry is immediate, then 2s for the 3rd)
            status_forcelist=(401, 404, 502, 503),
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.session.headers.update({"User-Agent": "pullapprove"})

        self.session.params.update(params)  # type: ignore
        self.session.headers.update(headers)

        if settings.get("CACHE", "file") == "file":
            CacheControl(
                self.session,
                cache=FileCache(os.path.join(tempfile.gettempdir(), "pullapprove")),
            )

        logger.debug(
            "%s.defaults headers=%s params=%s",
            self.__class__.__name__,
            self.session.headers,
            self.session.params,
        )

        self.mode = Mode()

    def get(self, *args, **kwargs) -> Any:
        return self._request(self.session.get, *args, **kwargs)

    def post(self, *args, **kwargs) -> Any:
        return self._request(self.session.post, *args, **kwargs)

    def put(self, *args, **kwargs) -> Any:
        return self._request(self.session.put, *args, **kwargs)

    def patch(self, *args, **kwargs) -> Any:
        return self._request(self.session.patch, *args, **kwargs)

    def delete(self, *args, **kwargs) -> Any:
        return self._request(self.session.delete, *args, **kwargs)

    def _request(self, to_call: Callable, url: str, *args, **kwargs) -> Any:
        # these kinds of requests either create, update, or delete data
        # and never run in test mode
        live_mode_only = (self.session.post, self.session.put, self.session.delete)

        ignore_mode = kwargs.pop(
            "ignore_mode", False
        )  # pop this first so it is never sent to request call
        if to_call in live_mode_only and self.mode.is_test() and not ignore_mode:
            logger.debug(
                f"Ignoring request in test mode url={url} args={args} kwargs={kwargs} method={to_call}"
            )
            return {}

        data: Any = []  # assume we're getting a list of objects by default

        if url.startswith("http://") or url.startswith("https://"):
            next_page_url = url
        else:
            # Automatically prepend the base url
            next_page_url = self.base_url + url

        page_items_key = kwargs.pop("page_items_key", None)
        user_error_status_codes = kwargs.pop("user_error_status_codes", {})
        parse_json = kwargs.pop("parse_json", True)

        while next_page_url:
            response = to_call(next_page_url, *args, **kwargs)
            from_cache = getattr(response, "from_cache", "disabled")
            logger.info(
                f"{self.__class__.__name__}.response status={response.status_code} url={next_page_url} args={args} kwargs={kwargs} method={to_call.__name__} from_cache={from_cache}"
            )
            logger.debug(response.headers)
            logger.debug(response.text)

            if "X-RateLimit-Remaining" in response.headers:
                canonical.set(
                    rate_limit_remaining=response.headers["X-RateLimit-Remaining"]
                )

            self._raise_exception_for_response(response, user_error_status_codes)

            if not parse_json:
                return response.text

            response_data = json_load(response.text)

            if isinstance(response_data, list):
                data = data + response_data
            elif isinstance(response_data, dict) and page_items_key:
                # we can still get a list of objects from a specific key
                data = data + response_data[page_items_key]
            else:
                # just immediately return whatever type this response gave
                return response_data

            next_page_url = response.links.get("next", {}).get("url", None)

            if not next_page_url and "next" in response_data:
                # Bitbucket pagination... could extract this but should work fine for now
                next_page_url = response_data["next"]

        return data

    def _raise_exception_for_response(
        self, response: requests.Response, invalid_status_codes: Dict[int, str]
    ) -> None:
        if response.status_code in invalid_status_codes:
            text = response.text
            try:
                # try to use github's message field if there is one
                text = response.json()["message"]
            except Exception:
                pass

            default_message = (
                f"{self.__class__.__name__} error (HTTP {response.status_code}): {text}"
            )

            raise UserError(
                invalid_status_codes.get(response.status_code, default_message)
            )

        response.raise_for_status()
