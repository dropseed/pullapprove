import os
from base64 import b64decode
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
import yaml
from cached_property import cached_property
from requests.exceptions import RequestException

from pullapprove.config.schema import Config, ExtendsLoader
from pullapprove.exceptions import UserError
from pullapprove.logger import logger
from pullapprove.models.base import BaseRepo

from .api import GitHubAPI
from .settings import GITHUB_API_BASE_URL

CONFIG_FILENAME = os.environ.get("CONFIG_FILENAME", ".pullapprove.yml")


class Repo(BaseRepo):
    def __init__(self, full_name: str, api_token: str) -> None:
        self.owner_name = full_name.split("/")[0]

        self._cached_team_users: Dict[str, List[str]] = {}

        api = GitHubAPI(
            f"{GITHUB_API_BASE_URL}/repos/{full_name}",
            headers={"Authorization": f"token {api_token}"},
            params={"per_page": 100},
        )

        super().__init__(full_name=full_name, api=api)

    def get_extra_as_dict(self) -> Dict[str, Any]:
        return {"owner_name": self.owner_name}

    def compile_url_shorthand(
        self, repo: str = "", filename: str = "", ref: str = ""
    ) -> str:
        url = f"{GITHUB_API_BASE_URL}/repos/{repo or self.full_name}/contents/{filename or CONFIG_FILENAME}"
        if ref:
            url = url + "?ref=" + ref
        return url

    def load_config(self, content: Optional[str]) -> Optional[Config]:
        if content is None:
            return None

        def get_url_response(url):
            if urlparse(url).netloc == urlparse(GITHUB_API_BASE_URL).netloc:
                return self.api.session.get(
                    url, headers={"Accept": "application/vnd.github.raw"}
                )
            return requests.get(url)

        extends_loader = ExtendsLoader(
            compile_shorthand=self.compile_url_shorthand,
            get_url_response=get_url_response,
        )

        config = Config(content, extends_loader.load)

        if config.data.get("github_api_version", ""):
            self.api.set_version(config.data["github_api_version"])

        return config

    def get_config_content(self, ref: Optional[str] = None) -> Optional[str]:
        url = f"/contents/{CONFIG_FILENAME}"

        try:
            data = self.api.get(url, params={"ref": ref})
        except RequestException:
            return None

        content = b64decode(data["content"]).decode("utf-8")
        return content

    @cached_property
    def teams(self) -> List[Dict[str, Any]]:
        return self.api.get("/teams")

    def get_usernames_in_team(self, team_slug: str) -> List[str]:
        team_slug = team_slug.lower().strip()

        if team_slug in self._cached_team_users:
            return self._cached_team_users[team_slug]

        # Check if the team has access to this repo (could potentially even skip this, but might run into user-permission errors later?)
        if not [x for x in self.teams if x["slug"].lower().strip() == team_slug]:
            # Nested teams don't show up in the teams list (but that is fewer API calls for all the ones that do)
            # so we'll double-check w/ the team-repo API
            try:
                # Doesn't return team data, just a 20X
                self.api.get(
                    f"{GITHUB_API_BASE_URL}/orgs/{self.owner_name}/teams/{team_slug}/repos/{self.full_name}",
                    user_error_status_codes={404: None},
                    parse_json=False,
                )
            except UserError:
                raise UserError(f"{team_slug} team was not found on this repository")

        # Craft the URL ourselves because that works with both nested and un-nested teams
        users = self.api.get(
            f"{GITHUB_API_BASE_URL}/orgs/{self.owner_name}/teams/{team_slug}/members",
        )
        usernames = [x["login"] for x in users]
        self._cached_team_users[team_slug] = usernames
        return usernames

    def get_open_pulls(self, branch: Optional[str] = None) -> List[Any]:
        params = {"state": "open", "sort": "updated", "direction": "desc"}
        if branch:
            params["head"] = f"{self.owner_name}:{branch}"
        return self.api.get("/pulls", params=params)
