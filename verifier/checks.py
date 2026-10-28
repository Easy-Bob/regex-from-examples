"""Checks shared by the tool verifiers. Pure functions of their arguments."""

import hashlib
import json

from .engine import DialectError, TooComplex, compile_pattern, matches


def result(valid, message, *, score=None, **details):
    return {
        "valid": valid,
        "score": float(valid) if score is None else score,
        "message": message,
        "details": details,
    }


def table_sha256(format_value, description, target, positives, negatives, max_length, heldout):
    """The digest pin_target gives its key; ``heldout`` as [(text, member)]."""
    rows = {
        "format": format_value,
        "description": description,
        "target": target,
        "positives": list(positives),
        "negatives": list(negatives),
        "max_length": max_length,
        "heldout": [[text, member] for text, member in heldout],
    }
    return hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def compiled(pattern):
    """(automaton, None), or (None, why the pattern is not in the dialect)."""
    try:
        return compile_pattern(pattern), None
    except (DialectError, TooComplex) as error:
        return None, str(error)


def misfits(machine, positives, negatives):
    """(given positives it misses, given negatives it matches)."""
    return [t for t in positives if not matches(machine, t)], [t for t in negatives if matches(machine, t)]


def shown(text):
    """A string as a message quotes it, the empty string included."""
    return "the empty string" if text == "" else json.dumps(text, ensure_ascii=False)
