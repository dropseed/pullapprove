import functools
from typing import Callable
from urllib.parse import quote_plus, urlparse

import click

from pullapprove.models.base import BasePullRequest
from pullapprove.models.bitbucket import PullRequest as BitbucketPullRequest
from pullapprove.models.bitbucket import Repo as BitbucketRepo
from pullapprove.models.github import PullRequest as GitHubPullRequest
from pullapprove.models.github import Repo as GitHubRepo
from pullapprove.models.gitlab import MergeRequest as GitLabMergeRequest
from pullapprove.models.gitlab import Repo as GitLabRepo

from .secrets import Secrets


def get_secret_value_for_url(url: str, host_type: str, secret_name: str) -> str:
    if not secret_name:
        parsed = urlparse(url)
        if not parsed.hostname:
            raise click.ClickException(f"Could not parse hostname from URL: {url}")
        secret_name = parsed.hostname

    secrets = Secrets()
    secret_value = secrets.get(secret_name)
    if not secret_value:
        if host_type == "github":
            prompt = 'To run PullApprove commands locally, we\'ll need a personal access token.\nThis will only be used for local commands/testing and can be removed at any time.\n\nEnter a GitHub personal access token with "repo" permission (https://github.com/settings/tokens)'
        elif host_type == "gitlab":
            prompt = 'To run PullApprove commands locally, we\'ll need a personal access token.\nThis will only be used for local commands/testing and can be removed at any time.\n\nEnter a GitLab personal access token with "read_api" permission'
        elif host_type == "bitbucket":
            prompt = 'To run PullApprove commands locally, we\'ll need an app password.\nThis will only be used for local commands/testing and can be removed at any time.\n\nEnter a Bitbucket app password with "pull_request:read" permission, using the format "{username}:{password}"'

        secret_value = secrets.prompt_set(secret_name, prompt=prompt)

    return secret_value


def get_pull_request_from_url(
    pull_request_url: str, host_type: str, secret_value: str
) -> BasePullRequest:
    parsed_url = urlparse(pull_request_url)
    path_parts = parsed_url.path.split("/")

    if host_type == "github":
        org_name = path_parts[1]
        repo_name = path_parts[2]
        pull_request_number = int(path_parts[4])
        return GitHubPullRequest(
            repo=GitHubRepo(f"{org_name}/{repo_name}", api_token=secret_value),
            number=pull_request_number,
        )
    elif host_type == "gitlab":
        if len(path_parts) < 7:
            full_name = "/".join(path_parts[1:3])
        else:
            # Has a subgroup
            full_name = "/".join(path_parts[1:4])

        project_id = quote_plus(full_name)
        number = int(path_parts[-1])

        return GitLabMergeRequest(
            repo=GitLabRepo(
                project_id=project_id,
                full_name=full_name,
                api_token=secret_value,
            ),
            number=number,
        )
    elif host_type == "bitbucket":
        workspace_id = path_parts[1]
        full_name = path_parts[1] + "/" + path_parts[2]
        number = int(path_parts[4])

        return BitbucketPullRequest(
            repo=BitbucketRepo(
                workspace_id=workspace_id,
                full_name=full_name,
                api_username_password=secret_value,
            ),
            number=number,
        )
    else:
        raise click.ClickException("Unknown host type: {}".format(host_type))


def pull_request_url_command(func: Callable) -> Callable:
    """A decorator that can be used for commands that parse URLs and prompt for secrets"""

    @click.option("--secret-name")
    @click.option(
        "--host-type",
        type=click.Choice(["github", "gitlab", "bitbucket"]),
        help="Specify the host type if it can't be guessed automatically.",
    )
    @click.argument("pull_request_url")
    @functools.wraps(func)
    def wrapper(*args, **kwargs):  # type: ignore
        host_type = kwargs.pop("host_type")
        secret_name = kwargs.pop("secret_name")
        pull_request_url = kwargs.pop("pull_request_url")

        if not host_type:
            if "github" in pull_request_url:
                host_type = "github"
            elif "gitlab" in pull_request_url:
                host_type = "gitlab"
            elif "bitbucket" in pull_request_url:
                host_type = "bitbucket"

        if not host_type:
            raise click.ClickException(
                "Host type not specified and could not be guessed."
            )

        secret_value = get_secret_value_for_url(
            pull_request_url, host_type, secret_name
        )
        pull_request = get_pull_request_from_url(
            pull_request_url, host_type, secret_value
        )

        return func(pull_request=pull_request, *args, **kwargs)

    return wrapper
