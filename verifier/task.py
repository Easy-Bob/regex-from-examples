"""The write-regex task's check: the submitted pattern allows exactly the strings the hidden target allows.

Four checks, in order. Failing one of the first three scores 0 and ends the judging. When the
pattern fits the given examples but is not equivalent to the target, it scores its balanced
accuracy on the held-out strings (the mean of the shares of members it matches and of non-members
it rejects), at most 0.99. Valid only when all four hold.
"""

from .checks import compiled, misfits, result, shown, table_sha256
from .engine import TooComplex, difference, matches

CHECKS = ["key-integrity", "well-formed", "fits-examples", "equivalent"]


def verdict(check, why, score=0.0, **details):
    return result(False, f"{check}: {why}", score=score, failed=check, **details)


def key_problem(arguments, reference):
    if reference is None:
        return "no answer key was pinned"
    if reference.format is not arguments.format:
        return f"the answer key is for {reference.format.value}, not {arguments.format.value}"
    heldout = [(item.text, item.member) for item in reference.heldout]
    digest = table_sha256(
        reference.format.value,
        reference.description,
        reference.target,
        reference.positives,
        reference.negatives,
        reference.max_length,
        heldout,
    )
    if reference.table_sha256 != digest:
        return "the answer key was altered: it no longer matches its sha256"
    machine, problem = compiled(reference.target)
    if problem:
        return f"the target is not in the dialect: {problem}"
    if any(misfits(machine, reference.positives, reference.negatives)):
        return "the target does not fit the given examples"
    if any(matches(machine, text) != member for text, member in heldout):
        return "the target labels a held-out string differently from the key"
    return None


def balanced_accuracy(machine, heldout):
    members = [matches(machine, item.text) for item in heldout if item.member]
    others = [not matches(machine, item.text) for item in heldout if not item.member]
    shares = [sum(group) / len(group) for group in (members, others) if group]
    return sum(shares) / len(shares)


def verify_task(arguments, output, reference, workspace):
    """``output``: a contract RegexOutput; ``reference``: pin_target's PinOutput."""
    problem = key_problem(arguments, reference)
    if problem:
        return verdict("key-integrity", problem)
    if output.format is not arguments.format:
        return verdict("well-formed", f"the pattern is for {output.format.value}, not {arguments.format.value}")
    if len(output.pattern) > reference.max_length:
        return verdict(
            "well-formed", f"the pattern is {len(output.pattern)} characters; at most {reference.max_length}"
        )
    machine, problem = compiled(output.pattern)
    if problem:
        return verdict("well-formed", problem)

    missed, matched = misfits(machine, reference.positives, reference.negatives)
    if missed:
        return verdict("fits-examples", f"it does not match the given example {shown(missed[0])}")
    if matched:
        return verdict("fits-examples", f"it matches the given counter-example {shown(matched[0])}")

    try:
        found = difference(machine, compiled(reference.target)[0])
    except TooComplex as error:
        return verdict("well-formed", f"the pattern is too complex to compare: {error}")
    if found is None:
        return result(True, f"All {len(CHECKS)} checks hold: the pattern allows exactly the format's strings.")
    score = min(0.99, round(balanced_accuracy(machine, reference.heldout), 4))
    wrong = (
        f"it allows {shown(found)}, which the format does not"
        if matches(machine, found)
        else f"it rejects {shown(found)}, which the format allows"
    )
    return verdict("equivalent", wrong, score=score, counterexample=found)
