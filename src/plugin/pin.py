"""pin_target, the write-regex task's reference: the format's hidden target and held-out strings,
out of the agent's sight."""

from __future__ import annotations

from pathlib import Path

from contract import FormatInput, Labeled, PinOutput
from plugin.formats import load_format
from verifier.checks import table_sha256


def pin_target(value: FormatInput, workspace: Path) -> PinOutput:
    data = load_format(value.format)
    heldout = [(text, member) for text, member in data["heldout"]]
    return PinOutput(
        format=value.format,
        description=data["description"],
        target=data["target"],
        positives=data["positives"],
        negatives=data["negatives"],
        max_length=data["max_length"],
        heldout=[Labeled(text=text, member=member) for text, member in heldout],
        table_sha256=table_sha256(
            value.format.value,
            data["description"],
            data["target"],
            data["positives"],
            data["negatives"],
            data["max_length"],
            heldout,
        ),
    )
