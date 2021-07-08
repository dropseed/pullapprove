from pullapprove.models.groups import Group
from pullapprove.models.states import ReviewState, State
from pullapprove.models.status import Status


def test_1_optional_group():
    g = Group("one")
    g.type = "optional"

    status = Status.from_groups([g])
    assert status.state == State.SUCCESS
    assert status.description == "No review groups are required"
    assert not status.is_approved()


def test_1_required_group():
    g = Group("one")

    status = Status.from_groups([g])
    assert status.state == State.PENDING
    assert status.description == "1 group pending"
    assert not status.is_approved()


def test_1_optional_1_required_group():
    g = Group("one")
    g.type = "optional"

    g2 = Group("two")
    g2.type = "required"

    status = Status.from_groups([g, g2])
    assert status.state == State.PENDING
    assert status.description == "1 group pending"
    assert not status.is_approved()


def test_1_optional_approved_group():
    g = Group("one")
    g.type = "optional"
    g.state = ReviewState.APPROVED

    status = Status.from_groups([g])
    assert status.state == State.SUCCESS
    assert status.description == "No review groups are required"
    assert not status.is_approved()


def test_1_required_approved_group():
    g = Group("one")
    g.state = ReviewState.APPROVED

    status = Status.from_groups([g])
    assert status.state == State.SUCCESS
    assert status.description == "1 group approved"
    assert status.is_approved()


def test_1_optional_approved_1_required_unapproved_group():
    g = Group("one")
    g.type = "optional"
    g.state = ReviewState.APPROVED

    g2 = Group("two")
    g2.type = "required"

    status = Status.from_groups([g, g2])
    assert status.state == State.PENDING
    assert status.description == "1 group pending"
    assert not status.is_approved()


def test_1_optional_unapproved_1_required_approved_group():
    g = Group("one")
    g.type = "optional"

    g2 = Group("two")
    g2.type = "required"
    g2.state = ReviewState.APPROVED

    status = Status.from_groups([g, g2])
    assert status.state == State.SUCCESS
    assert status.description == "1 group approved"
    assert status.is_approved()
