from pullapprove.context.functions import contains_any_fnmatches
from pullapprove.context.github import Files


def _get_files_sample():
    files = [
        {
            "sha": "abcdefg",
            "filename": f"app/views/test_{x}.py",
            "status": "modified",
            "additions": 1,
            "deletions": 0,
            "changes": 1,
            "blob_url": "https://blob_url",
            "raw_url": "https://raw_url",
            "contents_url": "https://contents_url",
            "patch": f"{x * 3 * '0'}",  # Fill with some characters
        }
        for x in range(5000)
    ]
    return Files(files)


def test_benchmark_include_speed(benchmark):
    files = _get_files_sample()

    def run():
        return files.include("app/views/test_1*.py")

    result = benchmark(run)
    assert len(result) == 1111


def test_benchmark_fnmatch_speed(benchmark):
    files = _get_files_sample()

    def run():
        return "app/views/test_1*.py" in files

    result = benchmark(run)
    assert result


def test_benchmark_contain_any_fnmatches_speed(benchmark):
    files = _get_files_sample()

    def run():
        return contains_any_fnmatches(files, ["app/views/test_1*.py"])

    result = benchmark(run)
    assert result


# These aren't exacly apples-to-apples comparision, but should give some idea of chaining impact


def test_benchmark_include_3_speed(benchmark):
    files = _get_files_sample()

    def run():
        return (
            files.include("app/views/test_1*.py")
            .exclude("app/views/test_2*.py")
            .exclude("app/views/test_3*.py")
        )

    result = benchmark(run)
    assert len(result) == 1111


def test_benchmark_include_6_speed(benchmark):
    files = _get_files_sample()

    def run():
        return (
            files.include("app/views/test_1*.py")
            .exclude("app/views/test_2*.py")
            .exclude("app/views/test_3*.py")
            .exclude("app/views/test_4*.py")
            .exclude("app/views/test_5*.py")
            .exclude("app/views/test_6*.py")
        )

    result = benchmark(run)
    assert len(result) == 1111


def test_benchmark_fnmatch_3_multiple_speed(benchmark):
    files = _get_files_sample()

    def run():
        return (
            "app/views/test_1*.py" in files
            and "app/views/test_2*.py" in files
            and "app/views/test_3*.py" in files
        )

    result = benchmark(run)
    assert result


def test_benchmark_fnmatch_6_multiple_speed(benchmark):
    files = _get_files_sample()

    def run():
        return (
            "app/views/test_1*.py" in files
            and "app/views/test_2*.py" in files
            and "app/views/test_3*.py" in files
            and "app/views/test_4*.py" in files
            and "app/views/test_5*.py" in files
            and "app/views/test_6*.py" in files
        )

    result = benchmark(run)
    assert result
