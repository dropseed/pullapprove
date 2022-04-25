import click
import cls_client

from .. import __version__
from .availability import availability
from .repl import repl
from .secrets import secrets
from .test import test

cls_client.set_project_key("cls_pk_UKzMHe3jUbvz8Ccgok1XC9jq")
cls_client.set_project_slug("pullapprove")
cls_client.set_version(__version__)
cls_client.set_ci_tracking_enabled(True)


@click.group()
def cli() -> None:
    pass


cli.add_command(availability)
cli.add_command(test)
cli.add_command(repl)
cli.add_command(secrets)


if __name__ == "__main__":
    cli()
