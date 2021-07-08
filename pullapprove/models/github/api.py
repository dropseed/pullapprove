from pullapprove.models.base import BaseAPI


class GitHubAPI(BaseAPI):
    def set_version(self, version: str) -> None:
        self.version = version
        api_version = self.version or "v3"
        self.session.headers.update(
            {"Accept": f"application/vnd.github.{api_version}+json"}
        )
