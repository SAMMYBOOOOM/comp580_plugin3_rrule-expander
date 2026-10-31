import inspect

import pytest

from contract import Task, Tool, TASKS, TOOLS
from plugin.expand_rrule import expand_rrule
from verifier import verify_input, verify_output, verify_task


def base(**overrides):
    values = {
        "dtstart": "20261001T090000",
        "rrule": "FREQ=DAILY",
        "window_start": "20261001T000000",
        "window_end": "20261005T235959",
        "max_occurrences": 100,
    }
    values.update(overrides)
    return values


def correct_output(**overrides):
    inputs = base()
    result = expand_rrule(**inputs)
    result.update(overrides)
    return inputs, result


def test_entry_point_arities():
    assert len(inspect.signature(verify_input).parameters) == 2
    assert len(inspect.signature(verify_output).parameters) == 4
    assert len(inspect.signature(verify_task).parameters) == 5


def test_tool_and_task_registration():
    assert Tool.EXPAND_RRULE in TOOLS
    assert Task.EXPAND_RRULE in TASKS


def test_verify_valid_input():
    assert verify_input(Tool.EXPAND_RRULE, base()) is None


def test_verify_valid_output():
    inputs, output = correct_output()

    assert verify_output(
        Tool.EXPAND_RRULE,
        inputs,
        output,
        None,
    ) is None


def test_verify_valid_task():
    inputs, output = correct_output()

    assert verify_task(
        Task.EXPAND_RRULE,
        [Tool.EXPAND_RRULE],
        inputs,
        output,
        None,
    ) is None


def test_verify_task_accepts_bare_tool_string():
    inputs, output = correct_output()

    assert verify_task(
        "expand-rrule",
        "expand_rrule",
        inputs,
        output,
        None,
    ) is None


def test_verify_rejects_unknown_tool():
    assert verify_input("unknown", base()) == "unknown tool"


def test_verify_rejects_unknown_task():
    assert verify_task(
        "unknown",
        ["expand_rrule"],
        base(),
        {},
        None,
    ) == "unknown task"


def test_verify_rejects_missing_tool():
    inputs, output = correct_output()

    assert verify_task(
        Task.EXPAND_RRULE,
        [],
        inputs,
        output,
        None,
    ) == "required tool expand_rrule is missing"


def test_verify_rejects_missing_input_field():
    inputs = base()
    del inputs["dtstart"]

    assert verify_input(Tool.EXPAND_RRULE, inputs) == "missing input field: dtstart"


def test_verify_rejects_wrong_input_type():
    inputs = base(dtstart=123)

    assert verify_input(Tool.EXPAND_RRULE, inputs) == "dtstart must be a string"


@pytest.mark.parametrize(
    "rule",
    [
        "",
        "FREQ=WEEKLY",
        "FREQ=DAILY;BYDAY=MO",
        "FREQ=DAILY;INTERVAL=0",
        "FREQ=DAILY;COUNT=0",
        "FREQ=DAILY;COUNT=2;UNTIL=20261003T090000",
    ],
)
def test_verify_rejects_invalid_rrule(rule):
    assert verify_input(
        Tool.EXPAND_RRULE,
        base(rrule=rule),
    ) is not None


def test_verify_rejects_boolean_output_limit():
    assert verify_input(
        Tool.EXPAND_RRULE,
        base(max_occurrences=True),
    ) == "max_occurrences must be an integer"


def test_verify_rejects_non_dictionary_output():
    inputs = base()

    assert verify_output(
        Tool.EXPAND_RRULE,
        inputs,
        [],
        None,
    ) == "output must be a dictionary"


def test_verify_rejects_missing_output_field():
    inputs, output = correct_output()
    del output["total_count"]

    assert verify_output(
        Tool.EXPAND_RRULE,
        inputs,
        output,
        None,
    ) == "missing field: total_count"


def test_verify_rejects_incorrect_occurrences():
    inputs, output = correct_output(
        occurrences=["20261001T090000"]
    )

    assert verify_output(
        Tool.EXPAND_RRULE,
        inputs,
        output,
        None,
    ).startswith("occurrences: expected")


def test_verify_rejects_incorrect_total_count():
    inputs, output = correct_output(total_count=99)

    assert verify_output(
        Tool.EXPAND_RRULE,
        inputs,
        output,
        None,
    ).startswith("total_count: expected")


def test_verify_rejects_integer_for_boolean():
    inputs, output = correct_output(truncated=1)

    assert verify_output(
        Tool.EXPAND_RRULE,
        inputs,
        output,
        None,
    ) == "truncated must be a boolean"


def test_verify_rejects_incorrect_truncation():
    inputs, output = correct_output(truncated=True)

    assert verify_output(
        Tool.EXPAND_RRULE,
        inputs,
        output,
        None,
    ).startswith("truncated: expected")


def test_verify_rejects_incorrect_normalized_rule():
    inputs, output = correct_output(normalized_rrule="FREQ=WEEKLY")

    assert verify_output(
        Tool.EXPAND_RRULE,
        inputs,
        output,
        None,
    ).startswith("normalized_rrule: expected")


def test_verify_rejects_boolean_total_count():
    inputs, output = correct_output(total_count=True)

    assert verify_output(
        Tool.EXPAND_RRULE,
        inputs,
        output,
        None,
    ) == "total_count must be an integer"


def test_verify_rejects_non_string_occurrences():
    inputs, output = correct_output(occurrences=[123])

    assert verify_output(
        Tool.EXPAND_RRULE,
        inputs,
        output,
        None,
    ) == "occurrences must contain only strings"


def test_verify_rejects_invalid_output_type():
    inputs, output = correct_output(normalized_rrule=123)

    assert verify_output(
        Tool.EXPAND_RRULE,
        inputs,
        output,
        None,
    ) == "normalized_rrule must be a string"


def test_verify_rejects_non_iterable_tools():
    assert verify_task(
        Task.EXPAND_RRULE,
        123,
        base(),
        {},
        None,
    ) == "tools must be a string or iterable"


def test_verify_rejects_non_dictionary_input():
    assert verify_input(Tool.EXPAND_RRULE, []) == "inputs must be a dictionary"


def test_verify_rejects_empty_window_output_correctly():
    inputs = base(
        rrule="FREQ=DAILY;COUNT=5",
        window_start="20261010T000000",
        window_end="20261012T000000",
    )
    output = expand_rrule(**inputs)

    assert output["occurrences"] == []

    assert verify_output(
        Tool.EXPAND_RRULE,
        inputs,
        output,
        None,
    ) is None


def test_verify_accepts_utc_output():
    inputs = base(
        dtstart="20261001T090000Z",
        rrule="FREQ=DAILY;COUNT=2",
        window_start="20261001T000000Z",
        window_end="20261003T000000Z",
    )
    output = expand_rrule(**inputs)

    assert verify_output(
        Tool.EXPAND_RRULE,
        inputs,
        output,
        None,
    ) is None