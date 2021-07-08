from pullapprove.config.schema import ExtendsLoader
from pullapprove.models.github import Repo


def test_extends_url():
    repo = Repo(full_name="dropseed/testing", api_token="")
    loader = ExtendsLoader(
        compile_shorthand=repo._compile_shorthand,
        get_url_response=lambda x: None,
    )
    url, field = loader.parse_string("https://www.dropseed.io/availability.json")
    assert url == "https://www.dropseed.io/availability.json"
    assert field == ""

    url, field = loader.parse_string(
        "https://www.dropseed.io/availability.json#key.deep[0]"
    )
    assert url == "https://www.dropseed.io/availability.json"
    assert field == "key.deep[0]"


def test_extends_local():
    repo = Repo(full_name="dropseed/testing", api_token="")
    loader = ExtendsLoader(
        compile_shorthand=repo._compile_shorthand,
        get_url_response=lambda x: None,
    )
    url, field = loader.parse_string("./availability.json")
    assert (
        url
        == "https://api.github.com/repos/dropseed/testing/contents/availability.json"
    )
    assert field == ""

    url, field = loader.parse_string("./availability.json#key.deep[0]")
    assert (
        url
        == "https://api.github.com/repos/dropseed/testing/contents/availability.json"
    )
    assert field == "key.deep[0]"


def test_extends_shorthand():
    repo = Repo(full_name="dropseed/testing", api_token="")
    loader = ExtendsLoader(
        compile_shorthand=repo._compile_shorthand,
        get_url_response=lambda x: None,
    )
    url, field = loader.parse_string("dropseed/another")
    assert (
        url == "https://api.github.com/repos/dropseed/another/contents/.pullapprove.yml"
    )
    assert field == ""

    url, field = loader.parse_string("dropseed/another#group.key")
    assert (
        url == "https://api.github.com/repos/dropseed/another/contents/.pullapprove.yml"
    )
    assert field == "group.key"

    url, field = loader.parse_string("dropseed/another@configs")
    assert (
        url
        == "https://api.github.com/repos/dropseed/another/contents/.pullapprove.yml?ref=configs"
    )
    assert field == ""

    url, field = loader.parse_string("dropseed/another@configs:availability.json")
    assert (
        url
        == "https://api.github.com/repos/dropseed/another/contents/availability.json?ref=configs"
    )
    assert field == ""

    url, field = loader.parse_string("dropseed/another@configs#group.key")
    assert (
        url
        == "https://api.github.com/repos/dropseed/another/contents/.pullapprove.yml?ref=configs"
    )
    assert field == "group.key"

    url, field = loader.parse_string("dropseed/another:availability.json")
    assert (
        url
        == "https://api.github.com/repos/dropseed/another/contents/availability.json"
    )
    assert field == ""

    url, field = loader.parse_string("dropseed/another:availability.json#key")
    assert (
        url
        == "https://api.github.com/repos/dropseed/another/contents/availability.json"
    )
    assert field == "key"
