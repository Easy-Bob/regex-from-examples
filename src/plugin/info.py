"""get_task: the format's description, its given examples and the length limit. Never the target."""

from __future__ import annotations

from pathlib import Path

from contract import TaskInput, TaskOutput
from plugin.formats import load_format


def get_task(value: TaskInput, workspace: Path) -> TaskOutput:
    data = load_format(value.format)
    return TaskOutput(
        format=value.format,
        description=data["description"],
        positives=data["positives"],
        negatives=data["negatives"],
        max_length=data["max_length"],
    )
