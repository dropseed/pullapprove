import json
from typing import TYPE_CHECKING, Optional
from urllib.parse import urlparse

import click
from click.types import File

from pullapprove.context.groups import Groups
from pullapprove.models.bitbucket import Repo, PullRequest
from pullapprove.models.groups import Group
from pullapprove.models.status import Status
from pullapprove.models.states import State, ReviewState
from pullapprove.logger import logger
from pullapprove.models.expressions import Expression

if TYPE_CHECKING:
    from pullapprove.models.base.pull_request import PullRequest as BasePullRequest


@click.group()
def test():
    pass


def bool_icon(value: Optional[bool]) -> str:
    if value is None:
        return click.style("?", dim=True)

    if value:
        return click.style("✔", fg="green")

    return click.style("🆇", fg="red")


def print_status(status: Status, format: str) -> None:
    if format == "json":
        print(json.dumps(status.as_dict(), indent=2))
        return

    state_colors = {
        State.ERROR: "red",
        State.PENDING: "yellow",
        State.SUCCESS: "green",
        State.FAILURE: "red",
        ReviewState.APPROVED: "green",
        ReviewState.REJECTED: "red",
        ReviewState.PENDING: "yellow",
    }

    click.secho(
        f"{status.state.capitalize()} - {status.description}",
        bold=True,
        fg=state_colors[status.state],
    )

    for group in status.groups:
        is_active = group.is_active
        click.echo()
        click.secho(group.name, bold=True, nl=False)
        if group.type != "required":
            click.secho(f" ({group.type}) ", nl=False)
        click.echo(" - ", nl=False)
        click.secho(group.state, fg=state_colors[group.state], nl=False)
        click.secho(f" [{group.score} of {group.required} required] ", nl=False)
        click.echo()

        if group.description:
            click.secho(f"  Description: {group.description}" + group.description)

        if group.conditions:
            click.secho("  Conditions:")
            for expression in group.conditions:
                click.secho(
                    f"    {bool_icon(expression.is_met)} {expression.expression_str}"
                )
        else:
            click.secho("  Conditions: []")

        if group.requirements:
            click.secho("  Requirements:")
            for expression in group.requirements:
                click.secho(
                    f"    {bool_icon(expression.is_met)} {expression.expression_str}"
                )
        else:
            click.secho("  Requirements: []")

        click.secho("  Reviewers:")
        for u in group.users_rejected:
            click.secho(f"    {bool_icon(False)} {u}")
        for u in group.users_approved:
            click.secho(f"    {bool_icon(True)} {u}")
        for u in group.users_pending:
            click.secho(f"    {bool_icon(None)} {u}")
        for u in group.users_available:
            click.secho(f"    - {u}")
        for u in group.users_unavailable:
            click.secho(f"    - {click.style(u, strikethrough=True)} (unavailable)")

    click.secho(
        "\n(Remember, this is just a test and does not reflect the status on the live PR)",
        italic=True,
        dim=True,
    )


def process_pull_request(pull_request: "BasePullRequest", config_file: File) -> Status:
    if config_file:
        config_content = config_file.read()  # type: ignore
    else:
        config_content = pull_request.repo.get_config_content(pull_request.base_ref)

    config = pull_request.repo.load_config(config_content)

    if not config.is_valid():
        click.secho(f"Invalid config:\n{config.validation_error}", fg="red", err=True)
        exit(1)

    if config.data.get("pullapprove_conditions", []):
        click.secho(
            "pullapprove_conditions are deprecated and not supported in the CLI, use overrides instead",
            err=True,
            fg="red",
        )

    groups = [
        Group.from_config(name, config_schema)
        for name, config_schema in config.data["groups"].items()
    ]
    status_from_groups, _ = pull_request.calculate_status(
        groups, users_unavailable=config.data["availability"]["users_unavailable"]
    )

    # Process the overrides (should move elsewhere at some point)
    ctx = pull_request.as_context()
    ctx["groups"] = Groups([x.as_dict() for x in groups])

    for override in config.data["overrides"]:  # type: ignore
        expr = Expression(override["if"])
        expr.load(ctx)
        if expr.is_met:
            # send override output (include groups in ctx)
            return Status(
                override["status"],
                description=(override["explanation"] or f"Override: {override['if']}"),
                groups=groups,
            )

    # Return the status without overrides
    return status_from_groups


@test.command("bitbucket")
# TODO keychain? something more user friendly - is that a separate step to save
@click.option("--api-username", envvar="BITBUCKET_API_USERNAME", required=True)
@click.option(
    "--api-password",
    envvar="BITBUCKET_API_PASSWORD",
    required=True,
    help="Needs pull_request:read permission",
)
@click.option("--config", "config_file", type=click.File("r"), required=False)
@click.option(
    "--format",
    "output_format",
    default="text",
    type=click.Choice(["json", "text"]),
    required=False,
)
@click.option("--debug", is_flag=True)
@click.argument("pull_request_url", type=str)
def bitbucket(
    pull_request_url, api_username, api_password, config_file, output_format, debug
):
    if output_format == "json" or not debug:
        logger.disabled = True

    parsed_url = urlparse(pull_request_url)
    path_parts = parsed_url.path.split("/")
    workspace_id = path_parts[1]
    full_name = path_parts[1] + "/" + path_parts[2]
    number = path_parts[4]

    repo = Repo(
        workspace_id=workspace_id,
        full_name=full_name,
        api_username_password=f"{api_username}:{api_password}",
    )

    pull_request = PullRequest(
        repo=repo,
        number=number,
    )

    status = process_pull_request(pull_request, config_file)

    print_status(status, output_format)
