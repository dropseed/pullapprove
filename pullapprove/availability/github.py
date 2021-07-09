import os
import json
import datetime

import dateparser

from .exceptions import ParseError


def handle_github_event(api):
    if "GITHUB_EVENT_PATH" in os.environ:
        with open(os.environ["GITHUB_EVENT_PATH"], "r") as f:
            github_event_data = json.load(f)
            github_event_action = github_event_data.get("action", "")

            if github_event_action in ("opened", "edited"):
                try:
                    issue = GitHubIssue(github_event_data["issue"])
                    api.post(
                        github_event_data["issue"]["comments_url"],
                        json={
                            "body": f"We've got it on the schedule!\n\n@{issue.username} will be unavailable from {issue.start_date} to {issue.end_date}.\n\nEdit the title of this issue to change the dates, or close the issue to remove it from the schedule."
                        },
                    )
                except ParseError as e:
                    error_message = str(e)
                    api.post(
                        github_event_data["issue"]["comments_url"],
                        json={
                            "body": f"There was an error parsing the issue.\n\n```{error_message}```\n"
                        },
                    )


def parse_issue_title(title):
    parts = title.split(" unavailable from ")
    if len(parts) != 2:
        raise ParseError(
            'Issue title should be in the format "@username unavailable from Date to Date"'
        )

    # username is the first word (can include "is", "will be", etc.)
    username = parts[0].split(" ")[0].strip().lstrip("@")
    dates = parts[1].strip()

    date_parts = dates.split(" to ")
    if len(date_parts) != 2:
        raise ParseError('Issue title needs dates in the format of "Date to Date"')

    start_date = dateparser.parse(date_parts[0])
    end_date = dateparser.parse(date_parts[1])

    if not start_date:
        raise ParseError("Unable to parse start date")

    if not end_date:
        raise ParseError("Unable to parse end date")

    start_date = start_date.date()
    end_date = end_date.date()

    if end_date < start_date:
        raise ParseError("The end date needs to be after the start date")

    return username, start_date, end_date


class GitHubIssue:
    def __init__(self, data):
        self.data = data
        self.username, self.start_date, self.end_date = parse_issue_title(
            self.data["title"]
        )

    def is_unavailable(self):
        # TODO timezone?
        today = datetime.datetime.now().date()
        return today >= self.start_date and today <= self.end_date

    def is_past(self):
        today = datetime.datetime.now().date()
        return today > self.end_date
