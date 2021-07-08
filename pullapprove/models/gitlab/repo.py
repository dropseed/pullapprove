import os
from base64 import b64decode
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from requests import RequestException

from pullapprove.models.base import BaseRepo

from .api import GitLabAPI
from .settings import GITLAB_API_BASE_URL

CONFIG_FILENAME = os.environ.get("CONFIG_FILENAME", ".pullapprove.yml")


class Repo(BaseRepo):
    def __init__(self, project_id: int, full_name: str, api_token: str) -> None:
        # TODO do we know owner name from full_name in gitlab? if so
        # then self.owner_name can happen in base

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

    def get_usernames_in_team(self, team_slug: str) -> List[str]:
        # https://docs.gitlab.com/ee/api/members.html
        return []
