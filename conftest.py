import json
import os

import pytest

from pullapprove.utils import json_load


@pytest.fixture
def testdata_objs():
    # uses a custon json.load that encodes dates
    return lambda name: json_load(
        open(
            os.path.join(
                os.path.dirname(__file__), "tests", "testdata", name + ".json"
            )
        ).read()
    )


@pytest.fixture
def testdata():
    return lambda name: json.load(
        open(
            os.path.join(
                os.path.dirname(__file__), "tests", "testdata", name + ".json"
            )
        )
    )
