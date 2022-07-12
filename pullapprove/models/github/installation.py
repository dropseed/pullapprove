import base64
import datetime
import json
import time
from typing import Dict, List, Optional

import jwt
from cached_property import cached_property

from pullapprove.logger import canonical, logger
from pullapprove.settings import settings

from .api import GitHubAPI
from .settings import GITHUB_API_BASE_URL


class Installation:
    def __init__(
        self,
        id: int,
        existing_api_token: Optional[str] = None,
        app_id: Optional[str] = None,
        app_private_key: Optional[str] = None,
    ) -> None:
        self.id = id
        self.existing_api_token = existing_api_token
        self.api = GitHubAPI(
            GITHUB_API_BASE_URL,
            headers={"Accept": "application/vnd.github.machine-man-preview+json"},
        )
        self.cache = self.api.cache  # reuse the API cache
        self.app_id = app_id or settings.get("GITHUB_APP_ID")
        self.app_private_key = app_private_key or settings.get("GITHUB_APP_PRIVATE_KEY")

    @cached_property
    def api_token(self) -> str:
        if self.existing_api_token:
            return self.existing_api_token

        return self._get_api_token()

    def get_repos(self) -> List[Dict]:
        headers = {"Authorization": f"token {self.api_token}"}
        return self.api.get(
            "/installation/repositories", headers=headers, page_items_key="repositories"
        )

    def _create_jwt(self) -> str:
        now = int(time.time())
        payload = {"iat": now, "exp": now + 60, "iss": self.app_id}
        decoded_key = base64.b64decode(self.app_private_key).decode(
            "utf-8"
        )  # assume we were given a base64 env variable
        encrypted = jwt.encode(payload, decoded_key, "RS256")
        return encrypted

    def _get_api_token(self) -> str:
        cache_key = f"github_installation:{self.id}"

        if self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                try:
                    cached_data = json.loads(cached)
                    expires = datetime.datetime.fromisoformat(cached_data["expires_at"])
                    if expires > datetime.datetime.utcnow() + datetime.timedelta(
                        minutes=15
                    ):
                        token = cached_data["token"]
                        canonical.set(token=token, token_expires=expires.isoformat())
                        return token
                except Exception as e:
                    logger.error(e, exc_info=e)
                    self.cache.delete(cache_key)

        data = self.api.post(
            f"/app/installations/{self.id}/access_tokens",
            headers={"Authorization": f"Bearer {self._create_jwt()}"},
            ignore_mode=True,
        )

        if self.cache:
            self.cache.set(
                cache_key,
                json.dumps(
                    {
                        "token": data["token"],
                        "expires_at": data["expires_at"].isoformat(),
                    }
                ).encode("utf-8"),
            )

        return data["token"]
