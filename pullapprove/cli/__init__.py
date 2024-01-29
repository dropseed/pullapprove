import click

from .. import __version__
from .availability import availability


@click.group()
def cli() -> None:
    pass


cli.add_command(availability)


if __name__ == "__main__":
    cli()
