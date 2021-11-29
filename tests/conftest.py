import json
import os

import pytest

from pullapprove.utils import json_load


@pytest.fixture
def testdata_objs():
    # uses a custon json.load that encodes dates
    return lambda name: json_load(
        open(os.path.join(os.path.dirname(__file__), "testdata", name + ".json")).read()
    )


@pytest.fixture
def testdata():
    return lambda name: json.load(
        open(os.path.join(os.path.dirname(__file__), "testdata", name + ".json"))
    )


def pytest_addoption(parser):
    parser.addoption(
        "--liveapi",
        action="store_true",
        dest="liveapi",
        default=False,
        help="enable liveapi decorated tests",
    )


def pytest_configure(config):
    # By default, liveapi tests are disabled
    # add --liveapi to run ALL tests
    if not config.option.liveapi:
        setattr(config.option, "markexpr", "not liveapi")
