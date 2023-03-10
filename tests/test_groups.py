from pullapprove.models.github.pull_request import PullRequest
from pullapprove.models.github.repo import Repo
from pullapprove.models.groups import Group
from pullapprove.models.reviews import Review, Reviewers


def test_group_as_dict_list_sorting():
    group1 = Group("one")
    group1.users = ["first", "second"]

    group2 = Group("one")
    group2.users = ["second", "first"]

    assert group1.users != group2.users
    assert group1.as_dict() == group2.as_dict()


def test_group_empty_teams(testdata, monkeypatch):
    group = Group("one")
    group.teams = ["team1"]

    pr = PullRequest(Repo("example", ""), 1)
    pr.__dict__["data"] = {"user": {"login": "dave"}}
    pr.__dict__["reviews"] = testdata("github_pr_reviews")
    pr.__dict__["requested_reviewers"] = {"users": []}
    monkeypatch.setattr(Repo, "get_usernames_in_team", lambda x, y: [])
    monkeypatch.setattr(Group, "load_conditions", lambda x, y, z: True)

    assert group.users_approved == []

    group.load_pr(pr, [], [], [])

    assert group.users_approved == []
