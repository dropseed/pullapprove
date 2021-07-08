from typing import Any, Dict, List, Tuple

from pullapprove.logger import logger


class Events:
    def __init__(self, items: List[Dict] = []) -> None:
        self._events: List[Event] = []
        for item in items:
            self.add(item["name"], item["data"])

    def __iter__(self):
        return iter(self._events)

    def add(self, name: str, data: Dict[str, Any]) -> None:
        event = Event(name, data)
        self._events.append(event)

    def used_command(self, command: str) -> Tuple[bool, str]:
        for event in self._events:
            used, remaining = event.used_command(command)
            if used:
                return used, remaining
        return False, ""


class Event:
    def __init__(self, name: str, data: Dict[str, Any]) -> None:
        self.name = name
        self.data = data

    def used_command(self, command: str) -> Tuple[bool, str]:
        # TODO will need gitlab comment events to be on webhook
        # and "Note Hook" event will be comment
        # https://docs.gitlab.com/ee/user/project/integrations/webhooks.html#comment-on-merge-request
        if self.name == "pull_request_review.submitted":
            body = self.data["review"]["body"]
            if body and body.startswith(command):
                remaining = body[len(command) :]
                logger.debug(f"{command} was used with remaining body of:\n{remaining}")
                return True, remaining

        return False, ""
