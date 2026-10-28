"""A scripted write-regex run: the case's pattern judged by the real verifier against the real key.

No model runs. A case (tests/cases/<name>.json) gives the format, the submitted pattern, optionally
another format named in the submission or a tamper applied to the key, and the verdict it expects.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from slimconfig import build_output, plain_output

import verifier
from contract import Format, FormatInput, RegexOutput

CASES = Path(__file__).parent / "cases"


def run_case(case: dict, workspace: Path, pinned: dict) -> dict:
    format = Format(case["format"])
    output = RegexOutput(format=Format(case.get("submit_format", format.value)), pattern=case["pattern"])
    reference = pinned[format]
    if case.get("tamper") == "altered-key":
        reference = replace(reference, target=reference.target + "?")
    elif case.get("tamper"):
        raise ValueError(f"unknown tamper {case['tamper']!r}")
    # The verifier gets contract instances, as NanoAgent's sandbox builds them from JSON.
    return verifier.verify_task(
        "write-regex",
        build_output({"format": format.value}, FormatInput),
        build_output(plain_output(output), RegexOutput),
        reference,
        str(workspace),
    )


def load_cases() -> list[dict]:
    return [json.loads(path.read_text()) | {"name": path.stem} for path in sorted(CASES.glob("*.json"))]
