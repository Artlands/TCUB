"""Deterministic, dependency-free path-glob matching for HPC-style paths.

Semantics (POSIX-path oriented, so the boundary is ``/``):

- ``**`` matches any run of characters *including* ``/`` (any depth).
- ``*``  matches any run of characters *except* ``/`` (one path segment).
- ``?``  matches a single character except ``/``.
- everything else matches literally.

Matching is anchored (a pattern must match the whole path). This is its own
tiny implementation rather than :mod:`fnmatch` so that ``*`` does *not* silently
cross directory separators -- an important property when a policy says a task may
read ``/projects/A/*`` but not ``/projects/A/secrets/B``.
"""

from __future__ import annotations

import re
from functools import lru_cache

__all__ = ["path_matches"]


@lru_cache(maxsize=4096)
def _compile(pattern: str) -> re.Pattern[str]:
    i, n = 0, len(pattern)
    out: list[str] = []
    while i < n:
        c = pattern[i]
        if c == "*":
            if i + 1 < n and pattern[i + 1] == "*":
                out.append(".*")  # '**' -> any depth, crosses '/'
                i += 2
            else:
                out.append("[^/]*")  # '*' -> one segment
                i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("".join(out) + r"\Z")


def path_matches(path: str, pattern: str) -> bool:
    """Return True iff ``path`` matches the glob ``pattern`` (whole-string)."""
    return _compile(pattern).match(path) is not None
