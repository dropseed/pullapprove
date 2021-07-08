from pullapprove.context.gitlab import MergeRequest


def test_merge_request_context(testdata):
    mr = MergeRequest(testdata("gitlab_mr"))
    assert mr.number == 2
