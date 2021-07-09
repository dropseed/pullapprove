import datetime

from pullapprove.availability.github import parse_issue_title


def test_availability_issue_parsing():
    username, start_date, end_date = parse_issue_title(
        "@davegaeddert unavailable from July 1, 2021 to July 5, 2021"
    )
    assert username == "davegaeddert"
    assert start_date == datetime.date(year=2021, month=7, day=1)
    assert end_date == datetime.date(year=2021, month=7, day=5)

    username, start_date, end_date = parse_issue_title(
        "davegaeddert unavailable from July 1, 2021 to July 5, 2021"
    )
    assert username == "davegaeddert"
    assert start_date == datetime.date(year=2021, month=7, day=1)
    assert end_date == datetime.date(year=2021, month=7, day=5)

    username, start_date, end_date = parse_issue_title(
        "@davegaeddert will be unavailable from July 1, 2021 to July 5, 2021"
    )
    assert username == "davegaeddert"
    assert start_date == datetime.date(year=2021, month=7, day=1)
    assert end_date == datetime.date(year=2021, month=7, day=5)
