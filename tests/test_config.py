from pullapprove.config.schema import Config


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
