"""The engine against Python's own ``re.fullmatch`` (with ``re.ASCII``) on random patterns of the dialect."""

from __future__ import annotations

import random
import re

import pytest

from verifier.engine import MAX_LENGTH, DialectError, fullmatch, parse

ATOMS = ["a", "b", "-", ".", "\\d", "\\w", "\\s", "\\.", "[ab]", "[^a]", "[a-c]", "[-a]", "\\D", "[\\d-]"]


def random_pattern(rng: random.Random, depth: int = 0) -> str:
    parts = []
    for _ in range(rng.randint(1, 3)):
        if depth < 2 and rng.random() < 0.3:
            inner = "|".join(random_pattern(rng, depth + 1) for _ in range(rng.randint(1, 3)))
            atom = rng.choice(["(", "(?:"]) + inner + ")"
        else:
            atom = rng.choice(ATOMS)
        atom += rng.choice(["", "", "*", "+", "?", "{2}", "{1,3}", "{0,}", "{2,}"])
        parts.append(atom)
    return "".join(parts)


def short_pattern(rng: random.Random) -> str:
    """A random pattern that fits the dialect's length limit."""
    while len(pattern := random_pattern(rng)) > MAX_LENGTH:
        pass
    return pattern


@pytest.mark.parametrize("seed", range(400))
def test_engine_agrees_with_python_re(seed: int) -> None:
    rng = random.Random(seed)
    pattern = short_pattern(rng)
    for _ in range(5):
        text = "".join(rng.choice("ab-.c1 \n") for _ in range(rng.randint(0, 7)))
        expected = re.fullmatch(pattern, text, re.ASCII) is not None
        assert fullmatch(pattern, text) is expected, (pattern, text)


@pytest.mark.parametrize(
    ("pattern", "text", "expected"),
    [
        ("(?:[01][0-9]|2[0-3]):[0-5][0-9]", "23:59", True),
        ("(?:[01][0-9]|2[0-3]):[0-5][0-9]", "24:00", False),
        ("[$€][0-9]+", "€12", True),
        ("[]a]+", "]a]", True),
        ("a{2,}", "aaaa", True),
        ("a{", "a{", True),
        ("x{1,x}", "x{1,x}", True),
        ("", "", True),
        ("(a|)b", "b", True),
        (".", "\n", False),
        ("\\w+", "café", False),
    ],
)
def test_known_matches(pattern: str, text: str, expected: bool) -> None:
    assert fullmatch(pattern, text) is expected
    assert (re.fullmatch(pattern, text, re.ASCII) is not None) is expected


@pytest.mark.parametrize(
    ("pattern", "message"),
    [
        ("^abc$", "anchors"),
        ("abc\\b", "anchor"),
        ("(?=a)a", "lookarounds"),
        ("(?i)abc", "flags"),
        ("(?P<x>a)", "named groups"),
        ("(a)\\1", "backreferences"),
        ("a*?", "lazy"),
        ("a++", "possessive"),
        ("*a", "nothing to repeat"),
        ("(ab", "closing ')'"),
        ("ab)", "unbalanced"),
        ("[ab", "closing ']'"),
        ("[z-a]", "wrong way round"),
        ("a{3,2}", "wrong way round"),
        ("a{21}", "up to 20"),
        ("\\x41", "not supported"),
        ("a" * 81, "at most 80"),
        ("ab\\", "lone backslash"),
    ],
)
def test_the_dialect_refuses_with_a_reason(pattern: str, message: str) -> None:
    with pytest.raises(DialectError, match=re.escape(message)):
        parse(pattern)
