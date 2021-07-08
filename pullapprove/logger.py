import logging
import os
import re
from io import StringIO
from typing import Any, Dict, List

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

if not logger.hasHandlers():
    # AWS sets a handler automatically, so this helps local
    logger.addHandler(logging.StreamHandler())


class SensitiveFormatter(logging.Formatter):
    """Formatter that remove tokens"""

    @staticmethod
    def _filter(s):
        bs = re.sub(r"Bearer [^\'\"\s]+", r"Bearer ******", s)
        return re.sub(r"token=\S+", r"token=******", bs)

    def format(self, record):
        original = logging.Formatter.format(self, record)
        return self._filter(original)


for handler in logger.handlers:
    handler.setFormatter(SensitiveFormatter())


class CanonicalLogLine:
    def __init__(self) -> None:
        self.data: Dict[str, Any] = {}

    def set(self, **kwargs) -> None:
        self.data.update(**kwargs)

    def clear(self) -> None:
        self.data = {}

    def emit(self) -> None:
        items = []
        for k, v in self.data.items():
            # TODO if spaces in v, then double quote it and escape inner quotes?
            items.append(f"{k}={v}")

        output = " ".join(items)
        logger.info("canonical-log-line %s", output)


canonical = CanonicalLogLine()

# A user-facing log that will be output in the report
# (messages should be single-line)
user_logger = logging.getLogger("pullapprove_user_logger")
user_logger.setLevel("DEBUG")
user_log_stream = StringIO()
user_log_handler = logging.StreamHandler(user_log_stream)
user_log_formatter = logging.Formatter("%(levelname)s:%(message)s")
user_log_handler.setFormatter(user_log_formatter)
user_logger.addHandler(user_log_handler)


def flush_user_logs() -> List[Dict[str, str]]:
    lines = []
    for message in user_log_stream.getvalue().splitlines():
        level, content = message.split(":", 1)
        lines.append(
            {
                "level": level,
                "content": content,
            }
        )

    # Clear out the logs
    user_log_stream.seek(0)
    user_log_stream.truncate()

    return lines


def reset_logs() -> None:
    """Clear out all the logs for a new invocation"""
    canonical.clear()
    flush_user_logs()
