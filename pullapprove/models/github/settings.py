import os

GITHUB_API_BASE_URL = os.environ.get("GITHUB_API_BASE_URL", "https://api.github.com")
if GITHUB_API_BASE_URL.endswith("/"):
    raise Exception('GITHUB_API_BASE_URL should not end with a "/"')
