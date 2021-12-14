from pullapprove.config.schema import Config, ExtendsLoader


def test_config_basic():
    content = """version: 3
groups:
  test: {}
"""
    config = Config(content)
    assert config.is_valid()


def test_config_pullapprove_conditions(snapshot):
    content = """version: 3

pullapprove_conditions:
- "'true'"
- condition: "'false'"
  unmet_status: pending
  explanation: "Custom explanation"

groups:
  test: {}
"""
    config = Config(content)
    assert config.is_valid()

    snapshot.assert_match(config.as_dict())


def test_config_extends_list():
    content = """version: 3
extends:
- a
- b
"""
    extends_loader = ExtendsLoader(
        compile_shorthand=lambda x: x, get_url_response=lambda x: x
    )
    config = Config(content, extends_loader.load)
    assert not config.is_valid()
    assert config.validation_error.messages["extends"][0] == "Not a valid string."
