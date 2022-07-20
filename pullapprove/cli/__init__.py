import click

from .. import __version__
from .availability import availability
from .repl import repl
from .secrets import secrets
from .test import test


@click.group()
def cli() -> None:
    pass


cli.add_command(availability)
cli.add_command(test)
cli.add_command(repl)
cli.add_command(secrets)


if __name__ == "__main__":
    cli()
