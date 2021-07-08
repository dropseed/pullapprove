from pullapprove.models.github.pull_request import PullRequest
from pullapprove.models.github.repo import Repo


def test_duplicate_labels(testdata, monkeypatch):
    pr = PullRequest(Repo(full_name="test", api_token="test"), 1)
    pr.repo.api.mode.set_test()
    pr.__dict__["data"] = {"labels": {}}

    final_labels = pr.set_labels(["a", "dup"], ["dup"])
    assert sorted(final_labels) == ["a", "dup"]
