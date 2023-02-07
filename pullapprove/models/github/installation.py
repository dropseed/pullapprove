import base64
import datetime
import json
import time
from typing import Dict, List, Optional

import jwt
from cached_property import cached_property

from pullapprove.logger import canonical, logger

from .api import GitHubAPI
from .settings import GITHUB_API_BASE_URL


class Installation:
    def __init__(
        self,
        app_id: str,
        app_private_key: str,
        id: Optional[int] = None,
        repo: Optional[str] = None,
    ) -> None:
        self.id = id
        self.repo = repo

        if not self.id and not self.repo:
            raise Exception("Must provide either installation ID or repo name")

        self.api = GitHubAPI(
            GITHUB_API_BASE_URL,
            headers={"Accept": "application/vnd.github.machine-man-preview+json"},
        )
        self.cache = self.api.cache  # reuse the API cache
        self.app_id = app_id
        self.app_private_key = app_private_key

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

    @cached_property
    def installation_id(self) -> int:
        if self.id:
            return self.id

        data = self.api.get(
            f"/repos/{self.repo}/installation",
            headers={"Authorization": f"Bearer {self._create_jwt()}"},
        )

        logger.debug(f"Retrieved installation ID {data['id']} for repo {self.repo}")

        return data["id"]

    @cached_property
    def api_token(self) -> str:
        cache_key = f"github_installation:{self.installation_id}"

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
            f"/app/installations/{self.installation_id}/access_tokens",
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
