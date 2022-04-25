import json
from typing import TYPE_CHECKING, Optional

import click
import cls_client
from click.types import File

from pullapprove.context.groups import Groups
from pullapprove.logger import logger
from pullapprove.models.expressions import Expression
from pullapprove.models.groups import Group
from pullapprove.models.states import ReviewState, State
from pullapprove.models.status import Status

from .utils import pull_request_url_command

if TYPE_CHECKING:
    from pullapprove.models.base.pull_request import BasePullRequest


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

    if not config:
        click.secho(f"No config found", fg="red", err=True)
        exit(1)

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

    for override in config.data["overrides"]:
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


@click.command()
@click.option("--config", "config_file", type=click.File("r"), required=False)
@click.option(
    "--format",
    "output_format",
    default="text",
    type=click.Choice(["json", "text"]),
    required=False,
)
@click.option("--debug", is_flag=True)
@pull_request_url_command
@cls_client.track_command(include_kwargs=["output_format", "debug"])
def test(pull_request, config_file, output_format, debug):  # type: ignore
    if output_format == "json" or not debug:
        logger.disabled = True

    status = process_pull_request(pull_request, config_file)

    print_status(status, output_format)
