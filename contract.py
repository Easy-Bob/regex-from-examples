"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    PIN_TARGET = "pin_target"
    GET_TASK = "get_task"
    TEST_REGEX = "test_regex"


class Task(Enum):
    WRITE_REGEX = "write-regex"


class Format(Enum):
    TIME24 = "time24"
    HEX_COLOR = "hex_color"
    SEMVER = "semver"
    US_ZIP = "us_zip"
    OCTET = "octet"
    IDENTIFIER = "identifier"
    SLUG = "slug"
    PRICE = "price"


FORMAT = "The bundled text format the regex must describe"
PATTERN = "A regex in the plugin's dialect (Python syntax without anchors, lookarounds or backreferences), at most 80 characters"


@dataclass
class Labeled(Output):
    text: Annotated[str, "A string"]
    member: Annotated[bool, "Whether the format allows it"]


@dataclass
class FormatInput(Output):
    format: Annotated[Format, FORMAT]


@dataclass
class PinOutput(Output):
    format: Annotated[Format, FORMAT]
    description: Annotated[str, "The format's description, as get_task gives it"]
    target: Annotated[str, "The hidden correct pattern"]
    positives: Annotated[list[str], "The given strings the format allows"]
    negatives: Annotated[list[str], "The given strings the format does not allow"]
    max_length: Annotated[int, "The longest pattern allowed"]
    heldout: Annotated[list[Labeled], "Hidden strings, labelled by the target, for partial credit"]
    table_sha256: Annotated[str, "The sha256 of every field above, as checks.table_sha256 computes it"]


@dataclass
class TaskInput(Output):
    format: Annotated[Format, FORMAT]


@dataclass
class TaskOutput(Output):
    format: Annotated[Format, FORMAT]
    description: Annotated[str, "Exactly which strings the format allows: the regex must follow it"]
    positives: Annotated[list[str], "Example strings the format allows"]
    negatives: Annotated[list[str], "Example strings the format does not allow"]
    max_length: Annotated[int, "The longest pattern allowed, in characters"]


@dataclass
class CheckInput(Output):
    format: Annotated[Format, FORMAT]
    pattern: Annotated[str, PATTERN]


@dataclass
class CheckOutput(Output):
    length: Annotated[int, "The pattern's length in characters"]
    fits: Annotated[bool, "Whether it matches every given positive and none of the given negatives"]
    missed_positives: Annotated[list[str], "Given positives the pattern does not match"]
    matched_negatives: Annotated[list[str], "Given negatives the pattern matches"]


@dataclass
class RegexOutput(Output):
    format: Annotated[Format, FORMAT]
    pattern: Annotated[str, PATTERN]


TOOLS = {
    Tool.PIN_TARGET: (FormatInput, PinOutput),
    Tool.GET_TASK: (TaskInput, TaskOutput),
    Tool.TEST_REGEX: (CheckInput, CheckOutput),
}

TASKS = {Task.WRITE_REGEX: (FormatInput, RegexOutput)}
