from pullapprove.models.gitlab import MergeRequest


def test_merge_request_context(testdata_objs):
    mr = MergeRequest(None, 1)
    mr.__dict__["data"] = testdata_objs("gitlab_mr")
    context = mr.as_context()
    assert context["number"] == 2
    assert context["author"] == "davegaeddert"
