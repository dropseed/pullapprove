from pullapprove.models.bitbucket import PullRequest, Repo


def test_bitbucket_set_reviewers():
    repo = Repo(workspace_id="test", full_name="test", api_username_password="test")
    repo.__dict__["workspace_members"] = [
        {
            "user": {
                "account_id": f"account_id_{x}",
                "nickname": f"nickname_{x}",
                "uuid": f"uuid_{x}",
            },
        }
        for x in range(10)
    ]
    repo.api.mode.set_test()

    pr = PullRequest(
        repo=repo,
        number=1,
    )
    pr.__dict__["data"] = {
        "title": "Title",
        "reviewers": [
            {
                "account_id": "account_id_1",
                "nickname": "nickname_1",
                "uuid": "uuid_1",
            },
            {
                "account_id": "account_id_2",
                "nickname": "nickname_2",
                "uuid": "uuid_2",
            },
        ],
    }
    updated_reviewers = pr.set_reviewers(
        users_to_add=["account_id_3", "nickname_4", "uuid_5"],
        users_to_remove=["account_id_1", "uuid_2", "nickname_3"],
        total_required=0,  # not implemented for bitbucket
    )

    assert updated_reviewers == [
        {
            "account_id": "account_id_4",
            "nickname": "nickname_4",
            "uuid": "uuid_4",
        },
        {
            "account_id": "account_id_5",
            "nickname": "nickname_5",
            "uuid": "uuid_5",
        },
    ]
