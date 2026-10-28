from .checks import compiled, misfits, result, table_sha256
from .engine import matches


def verify_input(value):
    return result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    if output_value.format is not input_value.format:
        return result(False, f"the key is for {output_value.format.value}, not {input_value.format.value}")
    heldout = [(item.text, item.member) for item in output_value.heldout]
    digest = table_sha256(
        output_value.format.value,
        output_value.description,
        output_value.target,
        output_value.positives,
        output_value.negatives,
        output_value.max_length,
        heldout,
    )
    if output_value.table_sha256 != digest:
        return result(False, "table_sha256 does not match the key")
    machine, problem = compiled(output_value.target)
    if problem:
        return result(False, f"the target is not in the dialect: {problem}")
    if any(misfits(machine, output_value.positives, output_value.negatives)):
        return result(False, "the target does not fit the given examples")
    if any(matches(machine, text) != member for text, member in heldout):
        return result(False, "the target labels a held-out string differently")
    return result(True, "the key is consistent", heldout=len(heldout))
