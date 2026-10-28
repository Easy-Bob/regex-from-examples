from __future__ import annotations

from pathlib import Path

import pytest

from contract import CheckInput, Format, TaskInput
from plugin import get_task, test_regex
from verifier.engine import DialectError


def test_get_task_gives_the_description_and_examples_but_not_the_target(tmp_path: Path, pinned: dict) -> None:
    info = get_task(TaskInput(format=Format.OCTET), tmp_path)
    assert "0 to 255" in info.description and "255" in info.positives and "1000" in info.negatives
    assert pinned[Format.OCTET].target not in repr(info)


def test_test_regex_reports_only_the_given_examples(tmp_path: Path) -> None:
    good = test_regex(CheckInput(format=Format.US_ZIP, pattern="[0-9]{5}(-[0-9]{4})?"), tmp_path)
    assert good.fits and good.missed_positives == [] and good.matched_negatives == []
    short = test_regex(CheckInput(format=Format.US_ZIP, pattern="[0-9]{5}"), tmp_path)
    assert not short.fits and short.missed_positives == ["90210-1234", "02139-4307"]
    # A near-miss the examples don't catch still "fits": only the verifier sees the held-out strings.
    assert test_regex(CheckInput(format=Format.OCTET, pattern="[0-9]{1,3}"), tmp_path).fits


def test_test_regex_explains_a_pattern_outside_the_dialect(tmp_path: Path) -> None:
    with pytest.raises(DialectError, match="anchors"):
        test_regex(CheckInput(format=Format.US_ZIP, pattern="^[0-9]{5}$"), tmp_path)
