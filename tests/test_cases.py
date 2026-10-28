from __future__ import annotations

from pathlib import Path

import pytest
from scripted import load_cases, run_case

CASES = load_cases()


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_case_gets_its_expected_verdict(case: dict, tmp_path: Path, pinned: dict) -> None:
    verdict = run_case(case, tmp_path, pinned)
    expect = case["expect"]
    assert verdict["valid"] is expect["valid"], verdict["message"]
    assert verdict["score"] == pytest.approx(expect["score"], abs=1e-4), verdict["message"]
    if expect["check"] is None:
        assert verdict["message"].startswith("All 4 checks hold"), verdict["message"]
    else:
        assert verdict["message"].startswith(expect["check"] + ":"), verdict["message"]


def test_the_cases_cover_every_check() -> None:
    from verifier.task import CHECKS

    assert set(CHECKS) <= {case["expect"]["check"] for case in CASES}


def test_every_format_has_a_target_and_an_equivalent_rewrite() -> None:
    from contract import Format

    names = {case["name"] for case in CASES}
    assert {f"{kind}_{fmt.value}" for fmt in Format for kind in ("gold", "alt")} <= names
