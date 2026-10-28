from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

from slimconfig import build_output, plain_output

import verifier
from contract import TOOLS, CheckInput, Format, FormatInput, TaskInput, Tool
from plugin import get_task, test_regex

# NanoAgent's sandbox lets a verifier import only these, contract and its own package.
ALLOWED_IMPORTS = {
    "__future__", "collections", "dataclasses", "decimal", "difflib", "enum", "fractions", "functools",
    "hashlib", "itertools", "json", "math", "operator", "pathlib", "re", "statistics", "string",
    "textwrap", "typing", "unicodedata",
}  # fmt: skip
FORBIDDEN_NAMES = {"__import__", "compile", "eval", "exec", "getattr", "globals", "open", "setattr", "vars"}


# The verifier gets contract instances, as NanoAgent's sandbox builds them from JSON.
def verify_input(tool: str, value: dict) -> dict:
    return verifier.verify_input(tool, build_output(value, TOOLS[Tool(tool)][0]))


def verify_output(tool: str, given: dict, made, workspace: Path) -> dict:
    given_class, made_class = TOOLS[Tool(tool)]
    return verifier.verify_output(
        tool, build_output(given, given_class), build_output(plain_output(made), made_class), str(workspace)
    )


def test_the_verifier_imports_only_what_the_sandbox_allows() -> None:
    for path in Path(verifier.__file__).parent.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                assert all(alias.name.split(".")[0] in ALLOWED_IMPORTS for alias in node.names), path.name
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                assert node.module.split(".")[0] in ALLOWED_IMPORTS | {"contract"}, path.name
            elif isinstance(node, ast.Name):
                assert node.id not in FORBIDDEN_NAMES, f"{path.name} uses {node.id}"
            elif isinstance(node, ast.Attribute):
                assert not node.attr.startswith("_"), f"{path.name} reaches {node.attr}"


def test_checks_what_the_types_cannot_say() -> None:
    assert verify_input("test_regex", {"format": "slug", "pattern": "[a-z]+"})["valid"] is True
    assert verify_input("test_regex", {"format": "slug", "pattern": "a" * 81})["valid"] is False


def test_tool_outputs_are_checked(tmp_path: Path) -> None:
    given = {"format": "semver"}
    assert verify_output("get_task", given, get_task(TaskInput(format=Format.SEMVER), tmp_path), tmp_path)["valid"]
    asked = {"format": "us_zip", "pattern": "[0-9]{5}"}
    made = test_regex(CheckInput(format=Format.US_ZIP, pattern="[0-9]{5}"), tmp_path)
    assert verify_output("test_regex", asked, made, tmp_path)["valid"] is True
    made.fits = True
    assert verify_output("test_regex", asked, made, tmp_path)["valid"] is False


def test_the_answer_key_is_checked(tmp_path: Path, pinned: dict) -> None:
    key = pinned[Format.TIME24]
    assert verify_output("pin_target", {"format": "time24"}, key, tmp_path)["valid"] is True
    assert verify_output("pin_target", {"format": "slug"}, key, tmp_path)["valid"] is False
    assert (
        verify_output("pin_target", {"format": "time24"}, replace(key, target="[0-9]{2}:[0-9]{2}"), tmp_path)["valid"]
        is False
    )


def test_the_task_input_is_the_reference_tools() -> None:
    assert TOOLS[Tool.PIN_TARGET][0] is FormatInput
