"""XP -> level curve.

A simple, tunable quadratic curve: level N requires N * 100 total XP more
than level N-1 needed. Kept as pure functions so the curve can be changed
in one place without touching service logic.
"""
from __future__ import annotations


def xp_required_for_level(level: int) -> int:
    """Total cumulative XP required to *reach* the given level."""
    if level <= 1:
        return 0
    return sum(n * 100 for n in range(1, level))


def level_for_xp(xp: int) -> int:
    """Compute the level corresponding to a total XP amount."""
    level = 1
    while xp >= xp_required_for_level(level + 1):
        level += 1
    return level


def xp_progress(xp: int) -> tuple[int, int, int]:
    """Return (current_level, xp_into_level, xp_needed_for_next_level)."""
    level = level_for_xp(xp)
    floor = xp_required_for_level(level)
    ceiling = xp_required_for_level(level + 1)
    return level, xp - floor, ceiling - floor
