import base64
import os

import pytest

from pullapprove.models.bitbucket.api import BitbucketAPI
from pullapprove.models.github.api import GitHubAPI
from pullapprove.models.gitlab.api import GitLabAPI


@pytest.mark.liveapi
def test_github_redis_cache():
    token = os.environ["TEST_GITHUB_API_TOKEN"]

    api = GitHubAPI(
        base_url="https://api.github.com",
        headers={"Authorization": f"token {token}"},
        cache_type="redis",
    )
    api.clear_cache()

    response = api.get("/user", return_response=True, params={"per_page": 1, "page": 1})
    response.raise_for_status()
    assert not response.from_cache
    assert response.json()["login"] == "davegaeddert"

    # also check the param sorting
    response = api.get("/user", return_response=True, params={"page": 1, "per_page": 1})
    response.raise_for_status()
    assert response.from_cache
    assert response.json()["login"] == "davegaeddert"

    # checking changing (removing) auth
    response = api.get(
        "/user",
        return_response=True,
        headers={"Authorization": ""},
        params={"page": 1, "per_page": 1},
    )
    assert response.status_code == 401


@pytest.mark.liveapi
def test_gitlab_redis_cache():
    token = os.environ["TEST_GITLAB_API_TOKEN"]

    api = GitLabAPI(
        base_url="https://gitlab.com/api/v4",
        headers={"Authorization": f"Bearer {token}"},
        cache_type="redis",
    )
    api.clear_cache()

    response = api.get("/user", return_response=True)
    response.raise_for_status()
    assert not response.from_cache
    assert response.json()["username"] == "davegaeddert"

    response = api.get("/user", return_response=True)
    response.raise_for_status()
    assert response.from_cache
    assert response.json()["username"] == "davegaeddert"


@pytest.mark.liveapi
def test_bitbucket_redis_cache():
    username = os.environ["TEST_BITBUCKET_API_USERNAME"]
    password = os.environ["TEST_BITBUCKET_API_PASSWORD"]
    api_username_password = f"{username}:{password}"

    api = BitbucketAPI(
        base_url="https://api.bitbucket.org/2.0",
        headers={
            "Authorization": "Basic "
            + base64.b64encode(api_username_password.encode("utf-8")).decode("utf-8")
        },
        cache_type="redis",
    )
    api.clear_cache()

    response = api.get("/user", return_response=True)
    response.raise_for_status()
    assert not response.from_cache
    assert response.json()["nickname"] == "davegaeddert"

    response = api.get("/user", return_response=True)
    response.raise_for_status()
    assert response.from_cache
    assert response.json()["nickname"] == "davegaeddert"
