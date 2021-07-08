from pullapprove.context import functions
from pullapprove.context.events import Event
from pullapprove.context.github import CheckRuns, Commits, Files, Statuses, User, Users
from pullapprove.models.github import PullRequest
from pullapprove.user_input import template


def test_patch_re_search_multiline():
    # mark_safe is in the patch, but not actually in the changes (+/-)
    s1 = "@@ -1,5 +1,5 @@\n from ebutils.decorators import cached_property\n from ebutils.html.utils import mark_safe\n \n-MODULE_TEXT = 'text'\n+MODULE_TEXT = 'texte'\n MODULE_IMAGE = 'image'"
    s2 = "@@ -1,5 +1,5 @@\n from ebutils.decorators import cached_property\n from ebutils.html.utils import mark_safe\n \n-MODULE_TEXT = 'text' mark_safe test\n+MODULE_TEXT = 'texte'\n MODULE_IMAGE = 'image'"
    pattern = r"(?m)^[\+\-].*(mark_safe|markSafe|as_unescaped_plaintext).*"
    assert not functions.contains_regex(s1, pattern)
    assert functions.contains_regex(s2, pattern)


# def test_patch_lines(testdata_objs):
#     files = Files(testdata_objs("github_pr_files"))
#     assert len(files) == 5
#     assert len(files.patches) == 5
#     assert len(files.lines_added) == 34
#     assert len(files.lines_removed) == 5
#     assert len(files.lines_modified) == 39
#     assert functions.contains_fnmatch(files.lines_added, "*widget*")


def test_event(testdata_objs):
    event = Event("pull_request.closed", testdata_objs("github_pull_request.closed"))
    assert event == "pull_request.closed"
    assert event.sender == "Codertocat"


def test_statuses(testdata_objs):
    statuses = Statuses(testdata_objs("github_pr_statuses"))
    assert "circleci" not in statuses
    assert "*/circleci" in statuses
    assert "ci/circleci" in statuses
    assert "ci/circleci*" in statuses
    # assert 'ci/circleci/test' in statuses
    assert "*circleci*" in statuses


def test_check_runs(testdata_objs):
    check_runs = CheckRuns(testdata_objs("github_pr_check_runs_chip")["check_runs"])
    assert "Build" not in check_runs
    assert "*/Build" not in check_runs
    assert "Build (main)" in check_runs
    assert "Build*" in check_runs
    assert "*Build*" in check_runs

    assert len(check_runs.successful) == 15
    assert len(check_runs.neutral) == 2
    assert len(check_runs.failed) == 0
    assert len(check_runs.skipped) == 0
    assert len(check_runs.completed) == 17
    assert len(check_runs.queued) == 0


def test_files():
    files = Files([{"filename": "app/templates/organization/home.html"}])
    assert "*.py" not in files
    assert "*.html" in files
    assert "templates/*" not in files
    assert "*/templates/*" in files


def test_files_filter_exclude():
    files = Files(
        [
            {"filename": "app/templates/organization/home.html"},
            {"filename": "app/templates/organization/base.html"},
        ]
    )
    assert len(files.include("*/templates/*")) == 2
    assert len(files.include("*/templates/*").exclude("*")) == 0
    assert len(files.include("*/templates/*").exclude("*base.html")) == 1
    assert len(files.include("nope")) == 0


def test_commits_signed_off(testdata_objs):
    # not signed pff
    commits_data = testdata_objs("github_pr_commits")
    commits = Commits(commits_data)
    assert not commits.are_signed_off
    assert not commits[0].is_signed_off

    # wrong email
    commits_data[0]["commit"][
        "message"
    ] = """Testing this out

Signed-off-by: dave <test@example.com>
    """
    commits = Commits(commits_data)
    assert not commits.are_signed_off
    assert not commits[0].is_signed_off

    # right email
    commits_data[0]["commit"][
        "message"
    ] = """Testing this out

Signed-off-by: support@github.com
    """
    commits = Commits(commits_data)
    assert commits.are_signed_off
    assert commits[0].is_signed_off

    # no commits
    commits = Commits([])
    assert commits.are_signed_off


def test_user():
    author = User({"login": "davegaeddert"})
    assert author is not "davegaeddert"  # this doesn't work yet
    assert author == "Davegaeddert"
    assert author == "davegaeddert"
    assert author != "joel "


def test_pr(testdata_objs):
    pr = PullRequest(None, 1)
    pr.__dict__["data"] = testdata_objs("github_pr")
    pr.__dict__["statuses"] = testdata_objs("github_pr_statuses")
    context = pr.as_context()

    assert (
        "Add" in context["title"]
    )  # uses fnmatch by default, which this doesn't match
    assert "Add*" not in context["title"]
    assert functions._contains(context["title"], functions.regex("Add.*"))
    assert functions.contains_regex(context["title"], "Add.*")

    assert functions.contains_fnmatch(context["head"], "dropseed:*")

    assert context["user"] == "davegaeddert"
    assert context["author"] == "davegaeddert"
    assert context["head"] == "dropseed:contact-info-privacy"
    assert context["head"].repo == "dropseed/testing"
    assert "dropseed*" in context["head"]
    assert "dropseed*" not in context["head"].repo.full_name  # doesn't use fnmatch

    assert "*circleci*" in context["statuses"]
    assert len(context["statuses"]) == 3
    assert len(context["statuses"].pending) == 2
    assert context["statuses"].pending.contexts == ["ci/circleci"]
    assert len(context["statuses"].failed) == 1
    assert context["statuses"].contexts == ["ci/circleci"]
    assert "ci/circleci" in context["statuses"].contexts
    assert "ci*" not in context["statuses"].contexts

    assert context["created_at"].month == 8
    assert context["created_at"] < context["date"]("august 17 2018")
    assert context["created_at"] < context["date"]("3 days ago")
    assert context["created_at"] > context["date"]("8/16 2018")
    assert context["created_at"] > context["date"]("10 years ago")

    assert template.render("{{ user }}", context) == "davegaeddert"
    assert template.render("{{ author }}", context) == "davegaeddert"


def test_users_list():
    assert (
        template.render(
            "{{ users }}",
            {"users": Users([{"login": "example1"}, {"login": "example2"}])},
        )
        == "example1, example2"
    )
    assert (
        template.render(
            "{{ text_list(users.mentions, 'and') }}",
            {"text_list": functions.text_list, "users": Users([{"login": "example1"}])},
        )
        == "@example1"
    )
    assert (
        template.render(
            "{{ text_list(users.mentions, 'and') }}",
            {
                "text_list": functions.text_list,
                "users": Users([{"login": "example1"}, {"login": "example2"}]),
            },
        )
        == "@example1 and @example2"
    )
    assert (
        template.render(
            "{{ text_list(users.mentions, 'and') }}",
            {
                "text_list": functions.text_list,
                "users": Users(
                    [
                        {"login": "example1"},
                        {"login": "example2"},
                        {"login": "example3"},
                    ]
                ),
            },
        )
        == "@example1, @example2 and @example3"
    )


def test_bool_object_list():
    # should be using the __len__ method
    nonempty = Users([{"login": "example1"}])
    empty = Users([])

    assert nonempty
    assert not empty


def test_contains_functions(testdata_objs):
    pr = PullRequest(None, 1)
    pr.__dict__["data"] = testdata_objs("github_pr")
    pr.__dict__["statuses"] = testdata_objs("github_pr_statuses")
    context = pr.as_context()

    assert functions._contains(context["title"], functions.regex("Add.*"))
    assert functions.contains_regex(context["title"], "Add.*")
    assert functions.contains_fnmatch(context["head"], "dropseed:*")
    assert functions.contains_any_fnmatches(context["head"], ["dropseed:*", "test"])
    assert not functions.contains_any_fnmatches(context["head"], ["dropsee:*", "test"])
    assert functions.contains_any_fnmatches(
        context["statuses"].failed, ["*circleci", "nope"]
    )
    assert not functions.contains_any_fnmatches(
        context["statuses"].succeeded, ["*circleci", "nope"]
    )


def test_random(testdata_objs):
    pr = PullRequest(None, 1)
    pr.__dict__["data"] = testdata_objs("github_pr")
    context = pr.as_context()

    # Results should be the same every time, but does change when you call it consecutively
    assert context["percent_chance"](33)
    assert not context["percent_chance"](33)
    assert not context["percent_chance"](0.33)
