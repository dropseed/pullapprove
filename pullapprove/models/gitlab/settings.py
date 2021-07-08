import os

GITLAB_API_BASE_URL = os.environ.get("GITLAB_API_BASE_URL", "https://gitlab.com/api/v4")
if GITLAB_API_BASE_URL.endswith("/"):
    raise Exception('GITLAB_API_BASE_URL should not end with a "/"')
