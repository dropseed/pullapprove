import os
import json

import click
import keyring
import cls_client
from appdirs import user_config_dir


class Secrets:
    def __init__(self):
        self.keyring_name = "pullapprove"

        # Store the names of secrets in our own JSON, but the secrets
        # themselves in the system keyring.
        self.user_config_dir = user_config_dir("pullapprove")
        self.secrets_file = os.path.join(self.user_config_dir, "secrets.json")

    def get_secret_names(self):
        if not os.path.exists(self.secrets_file):
            return []

        with open(self.secrets_file, "r") as f:
            secret_names = json.load(f)

        return secret_names

    def set_secret_names(self, secret_names):
        if not os.path.exists(self.user_config_dir):
            os.makedirs(self.user_config_dir)

        with open(self.secrets_file, "w+") as f:
            json.dump(secret_names, f)

    def get(self, secret_name):
        return keyring.get_password(self.keyring_name, secret_name)

    def set(self, secret_name, secret_value):
        keyring.set_password(self.keyring_name, secret_name, secret_value)

        with open(self.secrets_file, "r") as f:
            secret_names = json.load(f)

        if secret_name not in secret_names:
            secret_names.append(secret_name)
            with open(self.secrets_file, "w+") as f:
                json.dump(secret_names, f)

    def delete(self, secret_name):
        keyring.delete_password(self.keyring_name, secret_name)

        with open(self.secrets_file, "r") as f:
            secret_names = json.load(f)

        if secret_name in secret_names:
            secret_names.remove(secret_name)
            with open(self.secrets_file, "w+") as f:
                json.dump(secret_names, f)

    def list(self):
        with open(self.secrets_file, "r") as f:
            secret_names = json.load(f)

        for secret_name in secret_names:
            secret_value = self.get(secret_name)
            click.echo("{}={}".format(secret_name, secret_value))

    def prompt_set(self, secret_name, prompt="Value"):
        secret_value = click.prompt(prompt, hide_input=True)
        self.set(secret_name, secret_value)
        return secret_value


@click.group()
def secrets():
    """Manage API secrets used for local commands"""
    pass


@secrets.command()
@click.argument("name")
@cls_client.track_command("secrets_set")
def set(name):
    """Set a secret"""
    Secrets().prompt_set(name)
    click.secho(f'Secret "{name}" set.', fg="green")


@secrets.command()
@cls_client.track_command("secrets_list")
def list():
    """List names and values of stored secrets"""
    Secrets().list()
