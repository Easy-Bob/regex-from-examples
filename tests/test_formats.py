from __future__ import annotations

import pytest

from contract import Format
from plugin.formats import DATA
from plugin.tools_dev.build_formats import SPECS, build, serialize
from verifier.engine import compile_pattern, matches

SPEC = {spec.format: spec for spec in SPECS}


@pytest.mark.parametrize("fmt", list(Format))
def test_the_bundled_format_is_what_the_generator_builds(fmt: Format) -> None:
    assert (DATA / f"{fmt.value}.json").read_text() == serialize(build(SPEC[fmt]))


@pytest.mark.parametrize("fmt", list(Format))
def test_the_target_labels_every_string_as_the_key_says(fmt: Format, pinned: dict) -> None:
    key = pinned[fmt]
    machine = compile_pattern(key.target)
    assert all(matches(machine, text) for text in key.positives)
    assert not any(matches(machine, text) for text in key.negatives)
    assert all(matches(machine, item.text) == item.member for item in key.heldout)
    members = sum(item.member for item in key.heldout)
    assert members >= 90 and len(key.heldout) - members >= 90


@pytest.mark.parametrize("fmt", list(Format))
def test_every_boundary_value_is_held_out(fmt: Format, pinned: dict) -> None:
    held = {item.text for item in pinned[fmt].heldout}
    given = set(SPEC[fmt].positives) | set(SPEC[fmt].negatives)
    assert set(SPEC[fmt].boundaries) - given <= held
