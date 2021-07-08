from pullapprove.utils import fingerprint_for_data


def test_fingerprints_sorted_list():
    """Fingerprint does not know how to sort a list, expects it to be sorted already"""
    left = {"1": {"2": {"users": ["user1", "user2"]}}}
    right = {"1": {"2": {"users": ["user2", "user1"]}}}

    assert fingerprint_for_data(left) != fingerprint_for_data(right)


def test_fingerprints_sorted_dict():
    left = {"one": "ok", "two": "ok"}
    right = {"two": "ok", "one": "ok"}

    assert fingerprint_for_data(left) == fingerprint_for_data(right)


def test_fingerprints_sorted_dict_inequal():
    left = {"one": "ok", "three": "ok"}
    right = {"two": "ok", "one": "ok"}

    assert fingerprint_for_data(left) != fingerprint_for_data(right)
