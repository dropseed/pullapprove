import click

from .availability import availability
from .test import test
from .repl import repl
from .secrets import secrets


@click.group()
def cli():
    pass


cli.add_command(availability)
cli.add_command(test)
cli.add_command(repl)
cli.add_command(secrets)


if __name__ == "__main__":
    cli()
