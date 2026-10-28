"""The equivalence check against brute force: every string up to length 3 over one character of each kind."""

from __future__ import annotations

import itertools
import random

import pytest
from test_engine import short_pattern

from verifier.engine import compile_pattern, difference, matches

# One character of each kind the random patterns tell apart: a, b and c, a digit, "-", ".", "_", a
# space, a newline and "!" for everything else. The engine may show a character as another of the
# same kind, so counterexamples are compared by length and by what they mean.
KINDS = "abc0-._ \n!"
STRINGS = ["".join(t) for n in range(4) for t in itertools.product(KINDS, repeat=n)]


def first_disagreement(left: dict, right: dict) -> str | None:
    return next((s for s in STRINGS if matches(left, s) != matches(right, s)), None)


@pytest.mark.parametrize("seed", range(300))
def test_difference_agrees_with_brute_force(seed: int) -> None:
    rng = random.Random(seed)
    first, second = short_pattern(rng), short_pattern(rng)
    left, right = compile_pattern(first), compile_pattern(second)
    found = difference(left, right)
    brute = first_disagreement(left, right)
    if found is None:
        assert brute is None, (first, second, brute)
    else:
        assert matches(left, found) != matches(right, found), (first, second, found)
        if brute is not None:
            assert len(found) == len(brute), (first, second, found, brute)
        else:
            assert len(found) > 3


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("\\d{5}(-\\d{4})?", "[0-9]{5}(?:-[0-9]{4})?"),
        ("25[0-5]|2[0-4]\\d|1\\d\\d|[1-9]?\\d", "(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])"),
        ("([a-z0-9]+-)*[a-z0-9]+", "[a-z0-9]+(?:-[a-z0-9]+)*"),
        ("a*", "(a|aa)*"),
    ],
)
def test_differently_written_patterns_are_equivalent(first: str, second: str) -> None:
    assert difference(compile_pattern(first), compile_pattern(second)) is None


@pytest.mark.parametrize(
    ("first", "second", "shortest"),
    [
        ("[0-2][0-9]:[0-5][0-9]", "(?:[01][0-9]|2[0-3]):[0-5][0-9]", "24:00"),
        ("[0-9]{1,3}", "(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])", "00"),
        ("a+", "a*", ""),
    ],
)
def test_the_counterexample_is_the_shortest(first: str, second: str, shortest: str) -> None:
    assert difference(compile_pattern(first), compile_pattern(second)) == shortest
