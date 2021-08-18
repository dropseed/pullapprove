import base64
import os
from typing import Any, Dict, List, Optional

from cached_property import cached_property
from requests.exceptions import RequestException
import requests

from pullapprove.config.schema import Config, ExtendsLoader
from pullapprove.exceptions import UserError
from pullapprove.logger import logger
from pullapprove.models.base import BaseRepo

from .api import BitbucketAPI
from .settings import BITBUCKET_API_BASE_URL

CONFIG_FILENAME = os.environ.get("CONFIG_FILENAME", ".pullapprove.yml")


class Repo(BaseRepo):
    def __init__(
        self, workspace_id: str, full_name: str, api_username_password: str
    ) -> None:
        # confusing because the "Project" name is not in the workspace/repo name
        self.owner_name = full_name.split("/")[0]

        self.workspace_id = workspace_id

        self._cached_team_users: Dict[str, List[str]] = {}

        api = BitbucketAPI(
            f"{BITBUCKET_API_BASE_URL}/repositories/{full_name}",
            headers={
                "Authorization": "Basic "
                + base64.b64encode(api_username_password.encode("utf-8")).decode(
                    "utf-8"
                )
            },
            params={"pagelen": 100},
        )

        super().__init__(full_name=full_name, api=api)

    def get_extra_as_dict(self) -> Dict[str, Any]:
        return {"owner_name": self.owner_name}

    def get_config_content(self, ref: Optional[str] = None) -> Optional[str]:
        url = f"/src/{ref or 'master'}/{CONFIG_FILENAME}"

        try:
            data = self.api.get(url, parse_json=False)
        except RequestException:
            return None

        return data

    def compile_url_shorthand(
        self, repo: str = "", filename: str = "", ref: str = ""
    ) -> str:
        return f"{BITBUCKET_API_BASE_URL}/repositories/{repo or self.full_name}/src/{ref or 'master'}/{filename or CONFIG_FILENAME}"

    def load_config(self, content: Optional[str]) -> Optional[Config]:
        if content is None:
            return None

        extends_loader = ExtendsLoader(
            compile_shorthand=self.compile_url_shorthand,
            get_url_response=requests.get,
        )

        return Config(content, extends_loader.load)

    @cached_property
    def workspace_members(self) -> List[Dict]:
        return self.api.get(
            f"{BITBUCKET_API_BASE_URL}/workspaces/{self.workspace_id}/members",
            page_items_key="values",
        )
