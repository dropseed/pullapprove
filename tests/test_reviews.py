from pullapprove.models.github.pull_request import PullRequest
from pullapprove.models.reviews import Review
from pullapprove.models.states import ReviewState


def test_ignore_comments(testdata, monkeypatch):
    """Should ignore comments, and also d_redacted should have approved by the end"""
    pr = PullRequest(None, 1)
    pr.__dict__["reviews"] = testdata("github_pr_reviews")
    monkeypatch.setattr(PullRequest, "author", lambda x: "test")

    reviewers = pr.reviewers
    assert len(reviewers) == 4
    assert sorted(
        [x.username for x in reviewers.approved_for("test", behavior="optional")]
    ) == sorted(["p_redacted", "d_redacted", "j_redacted"])
    assert [
        x.username for x in reviewers.rejected_for("test", behavior="optional")
    ] == []

    # c_redacted has only left comments, so he is considered pending
    assert [x.username for x in reviewers.pending_for("test", behavior="optional")] == [
        "c_redacted"
    ]

    d_redacted = reviewers[0]
    assert [x.state for x in d_redacted.reviews] == [
        ReviewState.PENDING,
        ReviewState.APPROVED,
    ]


def test_is_for_none():
    body = """Hey this looks great"""
    review = Review(state="ok", body=body)
    assert review.is_for("test", behavior="optional")
    assert review.is_for("another", behavior="optional")


def test_is_for_single():
    body = """Hey this looks great
Reviewed-for: test"""
    review = Review(state="ok", body=body)
    assert review.is_for("test", behavior="optional")
    assert not review.is_for("another", behavior="optional")


def test_is_for_caseinsensitive():
    body = """Hey this looks great
reviewed-for: Test"""
    review = Review(state="ok", body=body)
    assert review.is_for("test", behavior="optional")
    assert not review.is_for("another", behavior="optional")


def test_is_for_multiline():
    body = """Hey this looks great
Reviewed-for: test

Reviewed-for: another
"""
    review = Review(state="ok", body=body)
    assert review.is_for("test", behavior="optional")
    assert review.is_for("another", behavior="optional")


def test_is_for_commas():
    body = """Hey this looks great

Reviewed-for: test, another
"""
    review = Review(state="ok", body=body)
    assert review.is_for("test", behavior="optional")
    assert review.is_for("another", behavior="optional")


def test_reviewed_for_required():
    assert Review(state="ok", body="nothing").is_for("test", behavior="optional")
    assert not Review(state="ok", body="nothing").is_for("test", behavior="required")
    assert not Review(state="ok", body="Reviewed-for: wrong").is_for(
        "test", behavior="required"
    )
    assert Review(state="ok", body="Reviewed-for: test").is_for(
        "test", behavior="required"
    )
    assert not Review(state="ok", body="Reviewed-for: testing").is_for(
        "test", behavior="required"
    )
    assert Review(state="ok", body="Reviewed-for: one, test").is_for(
        "test", behavior="required"
    )


def test_reviewed_for_ignored():
    assert Review(state="ok", body="nothing").is_for("test", behavior="optional")
    assert Review(state="ok", body="nothing").is_for("test", behavior="ignored")
    assert Review(state="ok", body="Reviewed-for: wrong").is_for(
        "test", behavior="ignored"
    )
    assert Review(state="ok", body="Reviewed-for: test").is_for(
        "test", behavior="ignored"
    )
    assert Review(state="ok", body="Reviewed-for: testing").is_for(
        "test", behavior="ignored"
    )
    assert Review(state="ok", body="Reviewed-for: one, test").is_for(
        "test", behavior="ignored"
    )
