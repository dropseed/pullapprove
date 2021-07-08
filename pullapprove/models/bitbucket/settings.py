import os

BITBUCKET_API_BASE_URL = os.environ.get(
    "BITBUCKET_API_BASE_URL", "https://api.bitbucket.org/2.0"
)
if BITBUCKET_API_BASE_URL.endswith("/"):
    raise Exception('BITBUCKET_API_BASE_URL should not end with a "/"')
