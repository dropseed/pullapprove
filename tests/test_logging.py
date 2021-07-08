from pullapprove.logger import flush_user_logs, user_logger


def test_user_log():
    user_logger.warning("deprecation warning!")
    assert flush_user_logs() == [
        {"level": "WARNING", "content": "deprecation warning!"}
    ]
