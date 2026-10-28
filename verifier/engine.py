"""A small regex engine for a safe subset of Python's regex syntax: parse, match, and decide equivalence.

The dialect behaves like Python's ``re.fullmatch`` with ``re.ASCII``, minus what could hang or what
the whole-string match makes pointless:

- literals (any Unicode character), ``.`` (any character but a newline), escapes ``\\d \\D \\w \\W
  \\s \\S \\n \\t \\r \\f \\v`` and any escaped non-alphanumeric character (``\\.``, ``\\-``, ...);
- character classes ``[...]`` with ranges and ``^`` negation;
- groups ``(...)`` and ``(?:...)``, alternation ``|``;
- quantifiers ``* + ? {n} {n,} {n,m}`` with counts up to 20.

Refused, with a message saying why: anchors (``^ $ \\b \\A \\Z``), lookarounds, backreferences,
named groups, flags, lazy or possessive quantifiers, other escapes, patterns over 80 characters.

A pattern becomes a Thompson automaton, which matches in time proportional to the pattern's size
times the string's length, never exponential. Two automata are equivalent when no string reaches an
accepting state in one but not the other: a breadth-first search over pairs of state sets finds the
shortest such string, or proves there is none. It lives in the verifier package, which may import
only the standard library; the plugin's tools import it from here.
"""

from itertools import pairwise

MAX_LENGTH = 80
MAX_COUNT = 20
MAX_STATES = 4000
MAX_PAIRS = 20000
TOP = 0x10FFFF

DIGIT = [(48, 57)]
WORD = [(48, 57), (65, 90), (95, 95), (97, 122)]
SPACE = [(9, 13), (32, 32)]
NAMED = {"n": 10, "t": 9, "r": 13, "f": 12, "v": 11}
# Characters a counterexample is shown with first, when its character range holds one of them.
PREFERRED = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ:.-_#$€ !"


class DialectError(ValueError):
    """The pattern is not in the dialect: the message says what and why."""


class TooComplex(ValueError):
    """The pattern needs more states than the engine allows."""


# ------------------------------------------------------------------ character sets


def normalized(intervals):
    """Sorted, merged, inclusive code point intervals."""
    merged = []
    for lo, hi in sorted(intervals):
        if merged and lo <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    return merged


def negated(intervals):
    result, start = [], 0
    for lo, hi in normalized(intervals):
        if lo > start:
            result.append((start, lo - 1))
        start = hi + 1
    if start <= TOP:
        result.append((start, TOP))
    return result


def contains(intervals, code):
    return any(lo <= code <= hi for lo, hi in intervals)


DOT = negated([(10, 10)])
CLASSES = {"d": DIGIT, "D": negated(DIGIT), "w": WORD, "W": negated(WORD), "s": SPACE, "S": negated(SPACE)}


# ------------------------------------------------------------------ parser
# Nodes: ("set", intervals) ("seq", [node]) ("alt", [node]) ("repeat", node, low, high or None)


def parse(pattern):
    """The pattern's syntax tree, or DialectError."""
    if len(pattern) > MAX_LENGTH:
        raise DialectError(f"the pattern is {len(pattern)} characters long; at most {MAX_LENGTH} are allowed")
    cursor = [0]
    node = parse_alternation(pattern, cursor)
    if cursor[0] < len(pattern):
        raise DialectError(f"unbalanced ')' at position {cursor[0]}")
    return node


def parse_alternation(pattern, cursor):
    branches = [parse_sequence(pattern, cursor)]
    while cursor[0] < len(pattern) and pattern[cursor[0]] == "|":
        cursor[0] += 1
        branches.append(parse_sequence(pattern, cursor))
    return branches[0] if len(branches) == 1 else ("alt", branches)


def counted(pattern, start):
    """(low, high or None, end) when a ``{n}``, ``{n,}`` or ``{n,m}`` quantifier starts at ``start``, else None."""
    end = pattern.find("}", start)
    if end < 0:
        return None
    body = pattern[start + 1 : end]
    low, comma, high = body.partition(",")
    if not low.isdigit() or not low.isascii() or (high and not (high.isdigit() and high.isascii())):
        return None
    return int(low), (int(high) if high else None) if comma else int(low), end + 1


def parse_sequence(pattern, cursor):
    items = []
    while cursor[0] < len(pattern) and pattern[cursor[0]] not in "|)":
        atom = parse_atom(pattern, cursor)
        if cursor[0] < len(pattern):
            char = pattern[cursor[0]]
            quantity = None
            if char in "*+?":
                quantity = {"*": (0, None), "+": (1, None), "?": (0, 1)}[char]
                cursor[0] += 1
            elif char == "{" and counted(pattern, cursor[0]):
                low, high, cursor[0] = counted(pattern, cursor[0])
                quantity = (low, high)
            if quantity:
                low, high = quantity
                if max(low, high or 0) > MAX_COUNT:
                    raise DialectError(f"repeat counts go up to {MAX_COUNT}")
                if high is not None and high < low:
                    raise DialectError(f"the repeat {{{low},{high}}} has its counts the wrong way round")
                if cursor[0] < len(pattern) and (
                    pattern[cursor[0]] in "*+?" or (pattern[cursor[0]] == "{" and counted(pattern, cursor[0]))
                ):
                    raise DialectError(
                        "a quantifier cannot follow another quantifier (lazy and possessive quantifiers are not supported)"
                    )
                atom = ("repeat", atom, low, high)
        items.append(atom)
    return items[0] if len(items) == 1 else ("seq", items)


def parse_atom(pattern, cursor):
    char = pattern[cursor[0]]
    if char == "(":
        if pattern.startswith("(?:", cursor[0]):
            cursor[0] += 3
        elif pattern.startswith("(?", cursor[0]):
            raise DialectError("only (...) and (?:...) groups are supported: no lookarounds, named groups or flags")
        else:
            cursor[0] += 1
        node = parse_alternation(pattern, cursor)
        if cursor[0] >= len(pattern) or pattern[cursor[0]] != ")":
            raise DialectError("a group is missing its closing ')'")
        cursor[0] += 1
        return node
    if char == "[":
        return ("set", parse_class(pattern, cursor))
    if char == "\\":
        return ("set", parse_escape(pattern, cursor))
    if char in "^$":
        raise DialectError("anchors ^ and $ are not needed: the pattern must always match the whole string")
    if char in "*+?" or (char == "{" and counted(pattern, cursor[0])):
        raise DialectError(f"the quantifier {char!r} at position {cursor[0]} has nothing to repeat")
    cursor[0] += 1
    return ("set", DOT if char == "." else [(ord(char), ord(char))])


def parse_escape(pattern, cursor):
    """The set a backslash escape stands for; the cursor ends past it."""
    if cursor[0] + 1 >= len(pattern):
        raise DialectError("the pattern ends with a lone backslash")
    char = pattern[cursor[0] + 1]
    cursor[0] += 2
    if char in CLASSES:
        return CLASSES[char]
    if char in NAMED:
        return [(NAMED[char], NAMED[char])]
    if char.isdigit():
        raise DialectError("backreferences such as \\1 are not supported")
    if char in "bBAZ":
        raise DialectError(f"\\{char} is an anchor; anchors are not needed: the whole string always has to match")
    if char.isascii() and char.isalnum():
        raise DialectError(f"the escape \\{char} is not supported")
    return [(ord(char), ord(char))]


def parse_class(pattern, cursor):
    """The intervals of a ``[...]`` class; the cursor ends past its ``]``."""
    cursor[0] += 1
    negate = cursor[0] < len(pattern) and pattern[cursor[0]] == "^"
    if negate:
        cursor[0] += 1
    intervals, first = [], True
    while True:
        if cursor[0] >= len(pattern):
            raise DialectError("a character class is missing its closing ']'")
        char = pattern[cursor[0]]
        if char == "]" and not first:
            cursor[0] += 1
            break
        first = False
        if char == "\\":
            low = parse_escape(pattern, cursor)
        else:
            low = [(ord(char), ord(char))]
            cursor[0] += 1
        if cursor[0] + 1 < len(pattern) and pattern[cursor[0]] == "-" and pattern[cursor[0] + 1] != "]":
            if len(low) != 1 or low[0][0] != low[0][1]:
                raise DialectError("a class like \\d cannot start a range")
            cursor[0] += 1
            if pattern[cursor[0]] == "\\":
                high = parse_escape(pattern, cursor)
                if len(high) != 1 or high[0][0] != high[0][1]:
                    raise DialectError("a class like \\d cannot end a range")
            else:
                high = [(ord(pattern[cursor[0]]), ord(pattern[cursor[0]]))]
                cursor[0] += 1
            if high[0][0] < low[0][0]:
                raise DialectError(f"the range {chr(low[0][0])}-{chr(high[0][0])} is the wrong way round")
            intervals.append((low[0][0], high[0][0]))
        else:
            intervals.extend(low)
    return negated(intervals) if negate else normalized(intervals)


# ------------------------------------------------------------------ automaton
# An automaton is {"start", "accept", "edges": [[(intervals, target)]], "empty": [[target]]}.


def compile_pattern(pattern):
    """The pattern's automaton, or DialectError or TooComplex."""
    machine = {"edges": [], "empty": []}
    start, accept = build(parse(pattern), machine)
    machine["start"], machine["accept"] = start, accept
    return machine


def new_state(machine):
    if len(machine["edges"]) >= MAX_STATES:
        raise TooComplex(f"the pattern needs more than {MAX_STATES} automaton states")
    machine["edges"].append([])
    machine["empty"].append([])
    return len(machine["edges"]) - 1


def build(node, machine):
    """Add ``node`` to the automaton: (its start state, its end state)."""
    kind = node[0]
    if kind == "set":
        start, end = new_state(machine), new_state(machine)
        machine["edges"][start].append((node[1], end))
        return start, end
    if kind == "seq":
        start = end = new_state(machine)
        for item in node[1]:
            first, last = build(item, machine)
            machine["empty"][end].append(first)
            end = last
        return start, end
    if kind == "alt":
        start, end = new_state(machine), new_state(machine)
        for branch in node[1]:
            first, last = build(branch, machine)
            machine["empty"][start].append(first)
            machine["empty"][last].append(end)
        return start, end
    _, inner, low, high = node
    start = end = new_state(machine)
    for _ in range(low):
        first, last = build(inner, machine)
        machine["empty"][end].append(first)
        end = last
    if high is None:
        loop = new_state(machine)
        first, last = build(inner, machine)
        machine["empty"][end].append(loop)
        machine["empty"][loop].append(first)
        machine["empty"][last].append(loop)
        end = loop
    else:
        finish = new_state(machine)
        for _ in range(high - low):
            first, last = build(inner, machine)
            machine["empty"][end].append(first)
            machine["empty"][end].append(finish)
            end = last
        machine["empty"][end].append(finish)
        end = finish
    return start, end


def closure(machine, states):
    """``states`` and every state reachable from them without reading a character."""
    seen, stack = set(states), list(states)
    while stack:
        for target in machine["empty"][stack.pop()]:
            if target not in seen:
                seen.add(target)
                stack.append(target)
    return frozenset(seen)


def step(machine, states, code):
    return closure(machine, [t for s in states for intervals, t in machine["edges"][s] if contains(intervals, code)])


def matches(machine, text):
    """Whether the automaton accepts the whole of ``text``."""
    states = closure(machine, [machine["start"]])
    for char in text:
        states = step(machine, states, ord(char))
        if not states:
            return False
    return machine["accept"] in states


def fullmatch(pattern, text):
    return matches(compile_pattern(pattern), text)


# ------------------------------------------------------------------ equivalence


def representative(low, high):
    """The character a counterexample shows for the range low..high: a familiar one when it holds one."""
    for char in PREFERRED:
        if low <= ord(char) <= high:
            return char
    for code in (low, 0x21, 0xA1):
        if low <= code <= high and not 0xD800 <= code <= 0xDFFF:
            return chr(code)
    return chr(high if not 0xD800 <= high <= 0xDFFF else low)


def blocks(*machines):
    """Ranges of characters every set in the automata treats alike, each with its representative."""
    cuts = {0, TOP + 1}
    for machine in machines:
        for edges in machine["edges"]:
            for intervals, _ in edges:
                for lo, hi in intervals:
                    cuts.update((lo, hi + 1))
    cuts = sorted(cuts)
    return [(lo, representative(lo, hi - 1)) for lo, hi in pairwise(cuts)]


def difference(first, second):
    """The shortest string one automaton accepts and the other rejects, or None when they are equivalent.

    Ties in length go to the string whose characters come first, range by range.
    """
    alphabet = blocks(first, second)
    start = (closure(first, [first["start"]]), closure(second, [second["start"]]))
    seen = {start}
    frontier = [(start, "")]
    while frontier:
        following = []
        for (left, right), text in frontier:
            if (first["accept"] in left) != (second["accept"] in right):
                return text
            for code, char in alphabet:
                pair = (step(first, left, code), step(second, right, code))
                if pair in seen or not (pair[0] or pair[1]):
                    continue
                if len(seen) >= MAX_PAIRS:
                    raise TooComplex(f"comparing the patterns needs more than {MAX_PAIRS} state pairs")
                seen.add(pair)
                following.append((pair, text + char))
        frontier = following
    return None
