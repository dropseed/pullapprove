import os
from base64 import b64decode
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote_plus

import requests
from requests import RequestException

from pullapprove.config.schema import Config, ExtendsLoader
from pullapprove.models.base import BaseRepo

from .api import GitLabAPI
from .settings import GITLAB_API_BASE_URL

CONFIG_FILENAME = os.environ.get("CONFIG_FILENAME", ".pullapprove.yml")


class Repo(BaseRepo):
    def __init__(
        self, project_id: Union[int, str], full_name: str, api_token: str
    ) -> None:
        self.project_id = project_id

        api = GitLabAPI(
            f"{GITLAB_API_BASE_URL}/projects/{self.project_id}",
            headers={"Authorization": f"Bearer {api_token}"},
        )

        super().__init__(full_name=full_name, api=api)

    def get_extra_as_dict(self) -> Dict[str, Any]:
        return {"project_id": self.project_id}

    def get_config_content(self, ref: Optional[str] = None) -> Optional[str]:
        url = f"/repository/files/{quote_plus(CONFIG_FILENAME)}"

        try:
            data = self.api.get(url, params={"ref": ref})
        except RequestException:
            return None

        content = b64decode(data["content"]).decode("utf-8")
        return content

    def compile_url_shorthand(
        self, repo: str = "", filename: str = "", ref: str = ""
    ) -> str:
        return f"{GITLAB_API_BASE_URL}/projects/{quote_plus(repo or self.full_name)}/repository/files/{quote_plus(filename or CONFIG_FILENAME)}?ref={ref or 'master'}"

    def load_config(self, content: Optional[str]) -> Optional[Config]:
        if content is None:
            return None

        extends_loader = ExtendsLoader(
            compile_shorthand=self.compile_url_shorthand,
            get_url_response=requests.get,
        )

        return Config(content, extends_loader.load)

    def get_usernames_in_team(self, team_slug: str) -> List[str]:
        # https://docs.gitlab.com/ee/api/members.html
        return []
