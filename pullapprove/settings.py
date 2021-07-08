import datetime
import os

from pullapprove.logger import logger


class MissingSettingError(Exception):
    pass


class Settings:
    def __init__(self, aws_ssm_parameter_path):
        self._aws_ssm_parameter_path = aws_ssm_parameter_path
        self._settings = {}
        self._ttl = 60 * 10  # 10 minutes
        self._expiration = None

    def refresh(self):
        logger.debug("Refreshing settings")

        settings = {}

        if self._aws_ssm_parameter_path:
            logger.debug("Fetching settings from AWS SSM")

            import boto3  # NOQA

            client = boto3.client("ssm")
            param_details = client.get_parameters_by_path(
                Path=self._aws_ssm_parameter_path, Recursive=True, WithDecryption=True
            )

            logger.debug(f"SSM params: {param_details}")

            if not param_details["Parameters"]:
                raise Exception(
                    f"No parameters found in AWS SSM {self._aws_ssm_parameter_path}: {param_details}"
                )

            for param in param_details["Parameters"]:
                # the name will be the last path component, uppercased later
                name = param["Name"].split("/")[-1]
                settings[name] = param["Value"]

        # add all env variables to available settings
        settings.update(os.environ)

        # save all settings to the instance
        for k, v in settings.items():
            # uppercase the name for consistency
            # and strip spaces on the value (empty " " will be treated as "")
            self._settings[k.upper()] = v.strip()

        logger.debug(f"Loaded settings: {self._settings}")

        self._expiration = datetime.datetime.now() + datetime.timedelta(
            seconds=self._ttl
        )

    def should_refresh(self):
        if self._expiration is None:
            return True

        return datetime.datetime.now() > self._expiration

    def get(self, key, default=None):
        if self.should_refresh():
            self.refresh()

        upper_key = key.upper()
        value = self._settings.get(upper_key, default)

        if value is None:
            raise MissingSettingError(f"{key} is missing and does not have a default")

        return value


settings = Settings(
    aws_ssm_parameter_path=os.environ.get("AWS_SSM_PARAMETER_PATH", None)
)
