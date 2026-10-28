"""test_regex's checks."""

from .checks import result
from .engine import MAX_LENGTH


def verify_input(value):
    if len(value.pattern) > MAX_LENGTH:
        return result(False, f"the pattern is {len(value.pattern)} characters; at most {MAX_LENGTH}")
    return result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    if output_value.length != len(input_value.pattern):
        return result(False, "length is not the pattern's length")
    if output_value.fits == bool(output_value.missed_positives or output_value.matched_negatives):
        return result(False, "fits must be true exactly when nothing is missed or wrongly matched")
    return result(True, "the test is consistent", fits=output_value.fits)
