from .checks import result


def verify_input(value):
    return result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    if output_value.format is not input_value.format:
        return result(False, f"the task is for {output_value.format.value}, not {input_value.format.value}")
    if not output_value.description or not output_value.positives or not output_value.negatives:
        return result(False, "the task needs a description and examples of both kinds")
    if set(output_value.positives) & set(output_value.negatives):
        return result(False, "a string is given both as an example and as a counter-example")
    return result(True, "the task is well formed", examples=len(output_value.positives) + len(output_value.negatives))
