"""Write the bundled formats, src/plugin/data/<format>.json, from the specs below.

Each format has a description, a hidden target pattern, a few given examples, and a held-out set
of about 200 strings for partial credit: random strings the target allows, near-misses made by
small edits to them, and the boundary values each spec lists. The engine labels every held-out
string with the target. A format is refused when the target is not in the dialect or labels a given
example differently from the spec. A seeded random source makes the files byte-identical every run.

    uv run python -m plugin.tools_dev.build_formats          # rebuild every format
    uv run python -m plugin.tools_dev.build_formats --check  # rebuild in memory, compare with the files
"""

from __future__ import annotations

import json
import random
import sys
from dataclasses import dataclass

from contract import Format
from plugin.formats import DATA
from verifier.engine import MAX_LENGTH, compile_pattern, matches, parse

HELDOUT_EACH = 100
PRINTABLE = [(0x20, 0x7E), (0x20AC, 0x20AC)]


@dataclass
class Spec:
    format: Format
    description: str
    target: str
    positives: list[str]
    negatives: list[str]
    boundaries: list[str]
    alphabet: str  # characters near-misses are made from


def pick(rng: random.Random, intervals: list[tuple[int, int]]) -> str:
    """A random character of the set, a printable one when the set has any."""
    usable = [
        (max(lo, plo), min(hi, phi)) for lo, hi in intervals for plo, phi in PRINTABLE if max(lo, plo) <= min(hi, phi)
    ]
    choices = usable or intervals
    lo, hi = rng.choice(choices)
    return chr(rng.randint(lo, hi))


def sample(rng: random.Random, node) -> str:
    """A random string the syntax tree allows."""
    kind = node[0]
    if kind == "set":
        return pick(rng, node[1])
    if kind == "seq":
        return "".join(sample(rng, item) for item in node[1])
    if kind == "alt":
        return sample(rng, rng.choice(node[1]))
    _, inner, low, high = node
    count = rng.randint(low, low + 3 if high is None else high)
    return "".join(sample(rng, inner) for _ in range(count))


def mutate(rng: random.Random, text: str, alphabet: str) -> str:
    """``text`` with one or two random edits: a character inserted, deleted or replaced."""
    for _ in range(rng.randint(1, 2)):
        at = rng.randint(0, len(text))
        edit = rng.choice(["insert", "delete", "replace"] if text else ["insert"])
        if edit == "insert":
            text = text[:at] + rng.choice(alphabet) + text[at:]
        elif edit == "delete":
            at = min(at, len(text) - 1)
            text = text[:at] + text[at + 1 :]
        else:
            at = min(at, len(text) - 1)
            text = text[:at] + rng.choice(alphabet) + text[at + 1 :]
    return text


def build(spec: Spec) -> dict:
    rng = random.Random(f"{spec.format.value}-580")
    tree, machine = parse(spec.target), compile_pattern(spec.target)
    given = set(spec.positives) | set(spec.negatives)
    members, others = {}, {}
    for text in spec.boundaries:
        (members if matches(machine, text) else others)[text] = None
    for _ in range(5000):
        if len(members) >= HELDOUT_EACH and len(others) >= HELDOUT_EACH:
            break
        text = sample(rng, tree)
        if len(members) < HELDOUT_EACH:
            members[text] = None
        changed = mutate(rng, text, spec.alphabet)
        (members if matches(machine, changed) else others)[changed] = None
    heldout = sorted(
        [[text, True] for text in members if text not in given][: HELDOUT_EACH + 20]
        + [[text, False] for text in others if text not in given][: HELDOUT_EACH + 20]
    )
    return {
        "format": spec.format.value,
        "description": spec.description,
        "target": spec.target,
        "positives": spec.positives,
        "negatives": spec.negatives,
        "max_length": MAX_LENGTH,
        "heldout": heldout,
    }


def check(spec: Spec) -> None:
    machine = compile_pattern(spec.target)
    wrong = [t for t in spec.positives if not matches(machine, t)] + [t for t in spec.negatives if matches(machine, t)]
    if wrong:
        raise SystemExit(f"{spec.format.value}: the target labels {wrong} differently from the spec")


def serialize(data: dict) -> str:
    return json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


SPECS = [
    Spec(
        Format.TIME24,
        "A 24-hour clock time HH:MM: exactly two digits for the hour, from 00 to 23, a colon, then exactly two "
        "digits for the minutes, from 00 to 59.",
        "(?:[01][0-9]|2[0-3]):[0-5][0-9]",
        ["00:00", "09:05", "12:30", "19:59", "23:59", "07:45"],
        ["7:45", "12:60", "12-30", "1230", "12:5", "30:00", ""],
        ["24:00", "23:60", "20:00", "00:59", "19:00", "2:00", "29:59", "23:5"],
        "0123456789:a ",
    ),
    Spec(
        Format.HEX_COLOR,
        "A CSS hex colour: # followed by exactly 3 or exactly 6 hexadecimal digits (0-9, a-f or A-F).",
        "#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})",
        ["#fff", "#000000", "#1A2b3C", "#abc", "#FFAA00", "#09f"],
        ["fff", "#ggg", "##fff", "#fffffff", "#", "# fff"],
        ["#ffff", "#12345", "#1234567", "#ABCDEF", "#abcdeg", "#12"],
        "0123456789abcdefgABCDEFG#",
    ),
    Spec(
        Format.SEMVER,
        "A version MAJOR.MINOR.PATCH: three whole numbers separated by dots. Each number is 0, or a number that "
        "does not start with 0 (so 0 and 10 are fine, 01 is not).",
        "(?:0|[1-9][0-9]*)\\.(?:0|[1-9][0-9]*)\\.(?:0|[1-9][0-9]*)",
        ["0.0.0", "1.2.3", "10.20.30", "1.0.0", "0.12.7", "999.0.1"],
        ["1.2", "1.2.3.4", "v1.2.3", "1..3", "1.2.x", "1.2.3 "],
        ["01.0.0", "0.01.0", "0.0.00", "00.0.0", "1.10.100", "0.0.10"],
        "0123456789.",
    ),
    Spec(
        Format.US_ZIP,
        "A US ZIP code: exactly 5 digits, optionally followed by a hyphen and exactly 4 more digits.",
        "[0-9]{5}(?:-[0-9]{4})?",
        ["12345", "00501", "90210-1234", "10001", "02139-4307"],
        ["1234", "123456", "12345-", "12345-123", "12345 6789", "ABCDE"],
        ["12345-12345", "1234-5678", "00000", "99999-9999", "-12345"],
        "0123456789- ",
    ),
    Spec(
        Format.OCTET,
        "A whole number from 0 to 255, written without leading zeros (0 itself is fine; 00 and 007 are not).",
        "(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])",
        ["0", "7", "42", "100", "199", "255"],
        ["-1", "1.5", "3a", "", "1 0", "1000"],
        ["00", "007", "256", "249", "250", "260", "300", "99", "010"],
        "0123456789",
    ),
    Spec(
        Format.IDENTIFIER,
        "A Python-style ASCII identifier: a letter (a-z or A-Z) or an underscore, followed by any number of "
        "letters, digits or underscores.",
        "[A-Za-z_][A-Za-z0-9_]*",
        ["x", "_private", "camelCase", "snake_case_2", "__init__", "A1"],
        ["2fast", "my-var", "", "has space", "café", "$dollar"],
        ["_", "__", "9", "a9", "_9", "Z"],
        "aZ_9-é $",
    ),
    Spec(
        Format.SLUG,
        "A URL slug: one or more words made of lowercase letters a-z and digits 0-9, joined by single hyphens. "
        "No leading, trailing or double hyphens.",
        "[a-z0-9]+(?:-[a-z0-9]+)*",
        ["hello", "hello-world", "a-b-c", "2024-recap", "x1-y2"],
        ["Hello", "hello_world", "-hello", "hello-", "", "hello world"],
        ["a--b", "a", "0", "a-0", "--", "-"],
        "abz09-_A ",
    ),
    Spec(
        Format.PRICE,
        "A price: a dollar sign $ or a euro sign €, then a whole number that does not start with 0 unless it is "
        "0 itself, then optionally a dot followed by exactly two digits.",
        "[$€](?:0|[1-9][0-9]*)(?:\\.[0-9]{2})?",
        ["$0", "$5", "€12", "$1999.99", "€0.50", "$10.00"],
        ["5", "$", "$5.5", "$5.", "$05", "€ 5", "£5"],
        ["€0", "$00", "$0.00", "$1.234", "€5.555", "$-5"],
        "0123456789.$€£",
    ),
]


def main() -> None:
    stale = []
    for spec in SPECS:
        check(spec)
        data = build(spec)
        path = DATA / f"{spec.format.value}.json"
        if "--check" in sys.argv[1:]:
            if not path.exists() or path.read_text() != serialize(data):
                stale.append(path.name)
        else:
            path.write_text(serialize(data))
        members = sum(1 for _, member in data["heldout"] if member)
        print(f"{spec.format.value}: {members} held-out members and {len(data['heldout']) - members} non-members")
    if stale:
        raise SystemExit(f"stale formats: {', '.join(stale)}; rebuild them")


if __name__ == "__main__":
    main()
