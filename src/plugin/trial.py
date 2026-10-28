"""test_regex: how a pattern does on the format's given examples only. A pattern outside the dialect
raises with the reason; the hidden target and held-out strings are never used."""

from __future__ import annotations

from pathlib import Path

from contract import CheckInput, CheckOutput
from plugin.formats import load_format
from verifier.checks import misfits
from verifier.engine import compile_pattern


def test_regex(value: CheckInput, workspace: Path) -> CheckOutput:
    data = load_format(value.format)
    missed, matched = misfits(compile_pattern(value.pattern), data["positives"], data["negatives"])
    return CheckOutput(
        length=len(value.pattern),
        fits=not (missed or matched),
        missed_positives=missed,
        matched_negatives=matched,
    )


# A tool, not a test for pytest to collect.
test_regex.__test__ = False
