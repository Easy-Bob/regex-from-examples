# Regex From Examples

A `nanoagent.plugin/v0001` plugin. Its task, `write-regex`, gives an agent the
exact description of a text format, such as a 24-hour time or a number from 0
to 255, with a few example strings. The agent writes a regex. A rule-based
verifier decides **exactly** whether the regex allows the same set of strings
as a hidden target, and if not, names the shortest string where they differ.

## Tools

| Tool | Does | Code |
|---|---|---|
| `pin_target` | The answer key: the format's hidden target pattern and about 200 held-out labelled strings, pinned before the agent starts | `src/plugin/pin.py` |
| `get_task` | The format's description, example strings it allows and does not allow, and the length limit | `src/plugin/info.py` |
| `test_regex` | How a pattern does on the given examples only: which examples it misses and which counter-examples it matches. A pattern outside the dialect is refused with the reason | `src/plugin/trial.py` |

### Tasks

| Task | Does | Runner |
|---|---|---|
| `write-regex` | Writes a regex that allows exactly the strings a format describes | `agent`, with `get_task` and `test_regex`; reference `pin_target` |

## The task

Regexes validate input everywhere and are easy to get almost right: a time
pattern that also takes `24:00`, a number pattern that takes `007`. The agent
reads a precise description and some examples, writes a pattern, and tests it
on the examples. The verifier then compares the pattern with the hidden
target on **every** string, not just the examples. Any equivalent pattern
passes, however it is written.

### The engine and its dialect (`verifier/engine.py`)

The plugin carries its own small regex engine. Python's `re` can take
exponential time on patterns like `(a+)+b`, and a verifier has no timeout.
The engine turns a pattern into an automaton, which matches in time
proportional to the pattern's size times the string's length. It lives in the
verifier package, which may import only the standard library, and the tools
import it from there.

- **Allowed:** literal characters (any Unicode), `.` (any character but a
  newline), `\d \D \w \W \s \S` with ASCII meanings, classes `[...]` with ranges
  and `^`, groups `(...)` and `(?:...)`, alternation `|`, and the quantifiers
  `* + ? {n} {n,} {n,m}` with counts up to 20. It behaves like Python's
  `re.fullmatch` with `re.ASCII`.
- **Refused, with the reason:** anchors (`^ $ \b \A \Z`), since the whole
  string must always match; lookarounds; backreferences; named groups; flags
  such as `(?i)`; lazy or possessive quantifiers; other escapes; patterns over
  80 characters.
- **Equivalence:** both patterns become automata. Characters are grouped into
  ranges every class treats alike, and a breadth-first search over pairs of
  state sets finds the shortest string one pattern accepts and the other
  rejects, or proves there is none. It stops at 20,000 state pairs, so a
  pattern too complex to compare is refused rather than analysed forever.

### The formats

The formats are bundled in `src/plugin/data/<format>.json`.
`src/plugin/tools_dev/build_formats.py` builds them from specs with a seeded
random source. It adds about 100 held-out strings each that the format allows
and does not allow: random members, near-misses made by small edits, and each
spec's boundary values. It refuses a format whose target labels a given
example wrongly.

| Format | Description, shortened | Edge cases |
|---|---|---|
| `time24` | `HH:MM`, hours 00–23, minutes 00–59 | `24:00`, `9:30` |
| `hex_color` | `#` and exactly 3 or 6 hex digits | 4 or 5 digits |
| `semver` | `MAJOR.MINOR.PATCH`, no leading zeros | `01.0.0` |
| `us_zip` | 5 digits, optionally `-` and 4 more | `12345-` |
| `octet` | 0 to 255, no leading zeros | `00`, `256` |
| `identifier` | a letter or `_`, then letters, digits or `_` (ASCII) | `2fast`, `café` |
| `slug` | lowercase words joined by single hyphens | `a--b`, `-a` |
| `price` | `$` or `€`, a number without leading zeros, optional `.` and 2 digits | `$05`, `€5.5` |

## The verifier

`verifier/task.py` runs four checks in order.

| # | Check | Fails when | Score |
|---|---|---|---|
| 1 | `key-integrity` | The key is altered (it no longer matches its sha256), is another format's, or its target mislabels a given or held-out string | 0 |
| 2 | `well-formed` | The pattern is for another format, is over 80 characters, is outside the dialect, or is too complex to compare | 0 |
| 3 | `fits-examples` | It misses a given example or matches a given counter-example | 0 |
| 4 | `equivalent` | Some string is allowed by one of the pattern and the target but not the other | balanced accuracy on the held-out strings, at most 0.99 |

Valid, and score 1.0, only when all four hold. The message names the failing
check and, for `equivalent`, the shortest string that tells them apart, e.g.
`equivalent: it allows "24:00", which the format does not`.

## Layout

It has the standard plugin layout, which NanoAgent requires:

```text
.
├── nanoagent.yaml   # manifest (a slimconfig ManifestConfig): id, runtime, permissions, tools, tasks
├── contract.py      # each tool's and task's typed input and output: slimconfig Output classes
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # needed environment variable names (none here)
├── src/plugin/      # the MCP server (__main__.py, its IMPLEMENTATIONS table), the tools, data/ and tools_dev/
├── tests/           # engine, equivalence, format, tool and verifier tests, and tests/cases/: scripted submissions with their verdicts
├── ui/              # outputs drawn from their JSON Schema
├── product/         # the product page a catalog shows: product.yaml and icon.svg
└── verifier/        # deterministic verifier package: engine.py (shared with the tools), one module per tool, and task.py for write-regex
```

## Develop and run

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
```

`uv run pytest` runs, without a model and without the network:
- the engine against Python's `re.fullmatch` on 400 random patterns;
- the equivalence check against brute force over every short string on 300
  random pattern pairs;
- the formats and every tool;
- `tests/cases/`: 33 scripted submissions, each with the verdict it expects
  (the target and an equivalent rewrite for every format, near-misses,
  overfitting, patterns outside the dialect and an altered key).

To rebuild the formats, or check the bundled ones are what the generator
builds:

```bash
uv run python -m plugin.tools_dev.build_formats --check
```
