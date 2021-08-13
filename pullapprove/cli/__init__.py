import click

from .availability import availability
from .test import test


@click.group()
def cli():
    pass


cli.add_command(availability)
cli.add_command(test)


if __name__ == "__main__":
    cli()
