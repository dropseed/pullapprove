from pullapprove.models.groups import Group


def test_group_as_dict_list_sorting():
    group1 = Group("one")
    group1.users = ["first", "second"]

    group2 = Group("one")
    group2.users = ["second", "first"]

    assert group1.users != group2.users
    assert group1.as_dict() == group2.as_dict()
