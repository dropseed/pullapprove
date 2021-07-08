import datetime
import fnmatch
import re
from random import Random
from typing import Any, Sequence
from typing.re import Pattern

import dateparser
from wcmatch import glob as wcglob

from pullapprove.exceptions import UserError

GLOB_FLAGS = wcglob.GLOBSTAR | wcglob.BRACE


# Custom class to instantiate a glob for use in _contains
class Glob:
    def __init__(self, s):
        self.pattern = s


def regex(s: str) -> Pattern:
    """
    `regex('WIP: .*')`
    """
    return re.compile(s)


def glob(s: str) -> Glob:
    """
    `glob('*.py')`
    """
    return Glob(s)


def date(s: str) -> datetime.datetime:
    """
    Parses a date from a string using [dateparser](https://dateparser.readthedocs.io/en/latest/).

    `date('3 days ago')`

    `date('8/10/1995')`
    """
    dt = dateparser.parse(s)
    if not dt:
        raise Exception(f"Unable to parse date: {s}")
    return dt


def _contains(items: Sequence, s: Any) -> bool:
    """Uses either fnmatch or regex depending on the type of object."""
    if isinstance(s, Pattern):
        return contains_regex(items, s)

    if isinstance(s, Glob):
        return contains_glob(items, s.pattern)

    return contains_fnmatch(items, s)


def _is_listlike(items: Any) -> bool:
    return isinstance(items, (list, tuple)) or hasattr(items, "_items")


def contains_fnmatch(items: Any, s: str) -> bool:
    """
    `contains_fnmatch(title, 'WIP*')`
    """
    if not _is_listlike(items):
        items = [items]
    items = [str(x) for x in items]

    return bool(fnmatch.filter(items, s))


def contains_any_fnmatches(items: Any, patterns: Sequence[str]) -> bool:
    """
    `contains_any_fnmatches(files, ['api/*', 'tests/*'])`
    """
    if not _is_listlike(items):
        items = [items]
    items = [str(x) for x in items]

    for pattern in patterns:
        if fnmatch.filter(items, pattern):
            return True

    return False


def contains_glob(items: Any, s: str) -> bool:
    """
    `contains_glob(file.filename, 'app/**/*.py')`
    """
    if not _is_listlike(items):
        items = [items]
    items = [str(x) for x in items]

    return bool(wcglob.globfilter(items, s, flags=GLOB_FLAGS))


def contains_any_globs(items: Any, patterns: Sequence[str]) -> bool:
    """
    `contains_any_globs(files, ['api/**', 'tests/*.py'])`
    """
    if not _is_listlike(items):
        items = [items]
    items = [str(x) for x in items]

    for pattern in patterns:
        if wcglob.globfilter(items, pattern, flags=GLOB_FLAGS):
            return True

    return False


def contains_regex(items: Any, s: str) -> bool:
    """
    `contains_regex(title, 'WIP.*')`
    """
    if not _is_listlike(items):
        items = [items]
    items = [str(x) for x in items]

    for item in items:
        if re.search(s, item):
            return True

    return False


def text_list(list_: Sequence, last_word: str = "or") -> str:
    """
    Returns a readable, comma-separated list of items for printing in templates.

    `text_list(['a', 'b', 'c', 'd']) == 'a, b, c or d'`

    `text_list(['a', 'b', 'c'], 'and') == 'a, b and c'`

    `text_list(['a', 'b'], 'and') == 'a and b'`

    `text_list(['a']) == 'a'`

    `text_list([]) == ''`
    """
    if not list_:
        return ""
    if len(list_) == 1:
        return str(list_[0])
    return "%s %s %s" % (
        ", ".join(str(i) for i in list_[:-1]),
        str(last_word),
        str(list_[-1]),
    )


class ContextRandom(Random):
    def percent_chance(self, percent_threshold):
        """
        Returns True if this PR is within the percent_chance

        `percent_chance(33)` will be True on roughly 1/3 of PRs
        """
        if percent_threshold > 1:
            percent_threshold = percent_threshold / 100

        if not (percent_threshold > 0 and percent_threshold < 1):
            raise UserError(
                "percent_chance should be between 1 and 100 (or 0.1 and 1.0)"
            )

        return self.random() < percent_threshold


def get_context_dictionary(random_seed):
    return {
        "all": all,
        "any": any,
        "length": len,
        "len": len,
        "count": len,
        "regex": regex,
        "glob": glob,
        "contains_fnmatch": contains_fnmatch,
        "contains_any_fnmatches": contains_any_fnmatches,
        "contains_glob": contains_glob,
        "contains_any_globs": contains_any_globs,
        "contains_regex": contains_regex,
        "date": date,
        "text_list": text_list,
        "percent_chance": ContextRandom(random_seed).percent_chance,
    }
