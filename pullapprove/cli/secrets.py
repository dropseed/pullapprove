import json
import os
from typing import Generator, List, Optional

import click
import cls_client
import keyring
from appdirs import user_config_dir


class Secrets:
    def __init__(self) -> None:
        self.keyring_name = "pullapprove"

        # Store the names of secrets in our own JSON, but the secrets
        # themselves in the system keyring.
        self.user_config_dir = user_config_dir("pullapprove")
        self.secrets_file = os.path.join(self.user_config_dir, "secrets.json")

    def get_secret_names(self) -> List[str]:
        if not os.path.exists(self.secrets_file):
            return []

        with open(self.secrets_file, "r") as f:
            secret_names: List[str] = json.load(f)

        return secret_names

    def set_secret_names(self, secret_names: List[str]) -> None:
        if not os.path.exists(self.user_config_dir):
            os.makedirs(self.user_config_dir)

        with open(self.secrets_file, "w+") as f:
            json.dump(secret_names, f)

    def get(self, secret_name: str) -> Optional[str]:
        return keyring.get_password(self.keyring_name, secret_name)

    def set(self, secret_name: str, secret_value: str) -> None:
        keyring.set_password(self.keyring_name, secret_name, secret_value)

        secret_names = self.get_secret_names()

        if secret_name not in secret_names:
            secret_names.append(secret_name)

        self.set_secret_names(secret_names)

    def delete(self, secret_name: str) -> None:
        keyring.delete_password(self.keyring_name, secret_name)

        secret_names = self.get_secret_names()

        if secret_name in secret_names:
            secret_names.remove(secret_name)

        self.set_secret_names(secret_names)

    def list(self) -> Generator:
        for secret_name in self.get_secret_names():
            secret_value = self.get(secret_name)
            yield secret_name, secret_value

    def prompt_set(self, secret_name: str, prompt: str = "Value") -> str:
        secret_value = click.prompt(prompt, hide_input=True)
        self.set(secret_name, secret_value)
        return secret_value


@click.group()
def secrets() -> None:
    """Manage API secrets used for local commands"""
    pass


@secrets.command()
@click.argument("name")
@cls_client.track_command("secrets_set")
def set(name: str) -> None:
    """Set a secret"""
    Secrets().prompt_set(name)
    click.secho(f'Secret "{name}" set.', fg="green")


@secrets.command()
@cls_client.track_command("secrets_list")
def list() -> None:
    """List names and values of stored secrets"""
    for secret_name, secret_value in Secrets().list():
        click.echo("{}={}".format(secret_name, secret_value))
