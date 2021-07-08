from pullapprove.models.groups import Group


def _user_approves(group, user):
    group.users_approved.append(user)
    group.users_pending.remove(user)
    group.score = len(group.users_approved)


def _update_pending(group, pr_number=10):
    group.users_pending += group.get_users_to_request(pr_number=pr_number)
    for u in group.users_pending:
        if u in group.users_available:
            group.users_available.remove(u)


def test_normal():
    group = Group("test")
    group.request = 1
    group.required = 1
    group.users_available = ["a", "b", "c"]
    group.request_order = "given"
    assert group.is_active

    _update_pending(group)
    assert group.users_pending == ["a"]
    assert group.users_available == ["b", "c"]

    _user_approves(group, "a")
    assert group.score == 1

    _update_pending(group)
    assert group.users_pending == []
    assert group.users_available == ["b", "c"]


def test_consistent_shuffle():
    # Make sure our manually seeded shuffle gets consistent results

    previous_pending = None

    for i in range(0, 10):
        # if you run this 10 times, the result should always be the same
        group = Group("test")
        group.request = 2
        group.required = 1
        group.users_available = ["a", "b", "c"]
        group.request_order = "shuffle"
        assert group.is_active

        _update_pending(group)

        if previous_pending is None:
            previous_pending = group.users_pending

        assert group.users_pending == previous_pending


# def test_round_robin():
#     expect = [
#         (0, ["a", "b"]),
#         (1, ["b", "c"]),
#         (2, ["c", "a"]),
#         (3, ["a", "b"]),
#         (4, ["b", "c"]),
#         (999, ["a", "b"]),
#         (1000, ["b", "c"]),
#     ]

#     for pr_number, expect_pending in expect:
#         group = Group("test")
#         group.request = 2
#         group.required = 1
#         group.users_available = ["a", "b", "c"]
#         group.request_order = "round_robin"
#         assert group.is_active

#         _update_pending(group, pr_number)
#         assert group.users_pending == expect_pending


def test_request_gt_required():
    group = Group("test")
    group.request = 2
    group.required = 1
    group.users_available = ["a", "b", "c"]
    group.request_order = "given"
    assert group.is_active

    _update_pending(group)
    assert group.users_pending == ["a", "b"]
    assert group.users_available == ["c"]

    _user_approves(group, "a")
    assert group.score == 1

    _update_pending(group)
    assert group.users_pending == ["b"]
    assert group.users_available == ["c"]

    _user_approves(group, "b")
    assert group.score == 2

    _update_pending(group)
    assert group.users_pending == []
    assert group.users_available == ["c"]


def test_request_all():
    group = Group("test")
    group.request = -1
    group.required = 1
    group.users_available = ["a", "b"]
    group.request_order = "given"
    assert group.is_active

    _update_pending(group)
    assert group.users_pending == ["a", "b"]
    assert group.users_available == []

    _user_approves(group, "a")
    assert group.score == 1

    # even if someone is added, they won't be asked
    group.users_available.append("c")
    _update_pending(group)
    assert group.users_pending == ["b"]
    assert group.users_available == ["c"]


def test_require_all():
    group = Group("test")
    group.request = 1
    group.required = -1
    group.users_available = ["a", "b", "c"]
    group.request_order = "given"
    assert group.is_active

    _update_pending(group)
    assert group.users_pending == ["a"]
    assert group.users_available == ["b", "c"]

    _user_approves(group, "a")

    _update_pending(group)
    assert group.users_pending == ["b"]
    assert group.users_available == ["c"]

    _user_approves(group, "b")

    _update_pending(group)
    assert group.users_pending == ["c"]
    assert group.users_available == []

    _user_approves(group, "c")

    _update_pending(group)
    assert group.users_pending == []
    assert group.users_available == []


def test_require_zero_request_gt_zero():
    group = Group("test")
    group.request = 2
    group.required = 0
    group.users_available = ["a", "b", "c"]
    group.request_order = "given"
    assert group.is_active

    _update_pending(group)
    assert group.users_pending == ["a", "b"]
    assert group.users_available == ["c"]

    _user_approves(group, "a")

    _update_pending(group)
    assert group.users_pending == ["b"]
    assert group.users_available == ["c"]

    _user_approves(group, "b")

    _update_pending(group)
    assert group.users_pending == []
    assert group.users_available == ["c"]


def test_require_zero_request_lt_zero():
    group = Group("test")
    group.request = -1
    group.required = 0
    group.users_available = ["a", "b", "c"]
    group.request_order = "given"
    assert group.is_active

    _update_pending(group)
    assert group.users_pending == ["a", "b", "c"]
    assert group.users_available == []

    _user_approves(group, "a")

    _update_pending(group)
    assert group.users_pending == ["b", "c"]
    assert group.users_available == []


def test_required_gt_request():
    group = Group("test")
    group.request = 1
    group.required = 2
    group.users_available = ["a", "b", "c"]
    group.request_order = "given"
    assert group.is_active

    _update_pending(group)
    assert group.users_pending == ["a"]
    assert group.users_available == ["b", "c"]

    _user_approves(group, "a")

    _update_pending(group)
    assert group.users_pending == ["b"]
    assert group.users_available == ["c"]

    _user_approves(group, "b")

    _update_pending(group)
    assert group.users_pending == []
    assert group.users_available == ["c"]


def test_request_gt_need():
    group = Group("test")
    group.request = 3
    group.required = 4
    group.users_available = ["a", "b", "c", "d", "e"]
    group.request_order = "given"
    assert group.is_active

    _update_pending(group)
    assert group.users_pending == ["a", "b", "c"]
    assert group.users_available == ["d", "e"]

    _user_approves(group, "a")

    _update_pending(group)
    assert group.users_pending == ["b", "c", "d"]
    assert group.users_available == ["e"]

    _user_approves(group, "b")

    _update_pending(group)
    assert group.users_pending == ["c", "d"]
    assert group.users_available == ["e"]
