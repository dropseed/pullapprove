import subprocess
import os
import json
import click

from pullapprove.models.github.api import GitHubAPI
from pullapprove.availability.github import handle_github_event, GitHubIssue


IS_CI = "CI" in os.environ


@click.group()
def availability():
    pass


@availability.command()
@click.option("--github-token", envvar="GITHUB_TOKEN", required=True)
@click.option("--github-repo", envvar="GITHUB_REPOSITORY", required=True)
@click.option(
    "--github-api-url",
    envvar="GITHUB_API_URL",
    default="https://api.github.com",
)
@click.argument("json_path", type=click.Path())
def sync_issues(json_path, github_token, github_repo, github_api_url):
    """
    Generate availability JSON by parsing GitHub Issues
    (also processes issue opened/edited events and responds with comments)
    """
    github_api = GitHubAPI(
        base_url=github_api_url,
        headers={
            "Authorization": f"token {github_token}",
        },
    )

    handle_github_event(github_api)

    with open(json_path, "r") as f:
        original_json_data = json.load(f)

    issues = github_api.get(f"/repos/{github_repo}/issues")

    users_unavailable = set()

    for i in issues:
        issue = GitHubIssue(i)

        unavailable = issue.is_unavailable()
        is_past = issue.is_past()

        if unavailable:
            click.secho(
                f"{issue.username} - {issue.start_date} → {issue.end_date} - unavailable",
                fg="yellow",
            )
        elif is_past:
            click.secho(
                f"{issue.username} - {issue.start_date} → {issue.end_date} - past",
                fg="red",
            )
        else:
            click.secho(
                f"{issue.username} - {issue.start_date} → {issue.end_date} - upcoming",
            )

        if is_past:
            github_api.patch(issue.data["url"], json={"state": "closed"})

        if unavailable:
            users_unavailable.add(issue.username)

    json_data = {"users_unavailable": list(users_unavailable)}

    if json_data != original_json_data:
        with open(json_path, "w+") as f:
            json.dump(json_data, f, indent=2, sort_keys=True)

        click.secho(
            f"{len(users_unavailable)} unavailable users written to {json_path}",
            fg="green",
        )

        if IS_CI:
            subprocess.check_call(["git", "config", "user.name", "github-actions"])
            subprocess.check_call(
                ["git", "config", "user.email", "github-actions@github.com"]
            )
            subprocess.check_call(["git", "add", json_path])
            # TODO list who was added in the commit messasge?
            subprocess.check_call(
                ["git", "commit", "-m", f"Update {json_path} automatically"]
            )
            subprocess.check_call(["git", "push"])

    else:
        click.secho(f"No changes to write to {json_path}", fg="yellow")
