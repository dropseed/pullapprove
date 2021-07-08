# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot

snapshots = Snapshot()

snapshots["test_config_pullapprove_conditions 1"] = {
    "config": {
        "availability": {"extends": "", "users_unavailable": []},
        "extends": "",
        "github_api_version": "",
        "groups": {
            "test": {
                "conditions": [],
                "description": "",
                "labels": {"approved": "", "pending": "", "rejected": ""},
                "meta": None,
                "requirements": [],
                "reviewers": {"teams": [], "users": []},
                "reviews": {
                    "author_value": 0,
                    "request": 1,
                    "request_order": "random",
                    "required": 1,
                    "reviewed_for": "optional",
                },
                "type": "required",
            }
        },
        "meta": None,
        "notifications": [],
        "overrides": [],
        "pullapprove_conditions": [
            {"condition": "'true'", "explanation": "", "unmet_status": "success"},
            {
                "condition": "'false'",
                "explanation": "Custom explanation",
                "unmet_status": "pending",
            },
        ],
        "version": 3,
    },
    "config_text": """version: 3

pullapprove_conditions:
- "\'true\'"
- condition: "\'false\'"
  unmet_status: pending
  explanation: "Custom explanation"

groups:
  test: {}
""",
}
