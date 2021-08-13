from typing import Any, Dict, List, Optional

from pullapprove.config.schema import Config


class BaseRepo:
    def __init__(self, full_name, api) -> None:
        self.full_name = full_name
        self.api = api

    def as_dict(self) -> Dict[str, Any]:
        # Report should be able to depend on these keys
        data = {"full_name": self.full_name}
        data.update(self.get_extra_as_dict())
        return data

    def get_extra_as_dict(self) -> Dict[str, Any]:
        return {}

    def compile_url_shorthand(
        self, repo: str = "", filename: str = "", ref: str = ""
    ) -> str:
        raise NotImplementedError

    def load_config(self, content: Optional[str]) -> Optional[Config]:
        raise NotImplementedError

    def get_config_content(self, ref: Optional[str] = None) -> Optional[str]:
        raise NotImplementedError

    def get_usernames_in_team(self, team_slug: str) -> List[str]:
        raise NotImplementedError
