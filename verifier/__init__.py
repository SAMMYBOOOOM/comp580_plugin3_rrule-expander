from datetime import UTC, datetime, timedelta, timezone

from contract import TASKS, TOOLS, Task, Tool


def _parse_datetime(value, field):
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")

    formats = (
        ("%Y%m%dT%H%M%SZ", True),
        ("%Y%m%dT%H%M%S", False),
    )

    for fmt, utc in formats:
        try:
            parsed = datetime.strptime(value, fmt)
            if parsed.strftime(fmt) != value:
                continue
            if utc:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed
        except ValueError:
            continue

    raise ValueError(
        f"{field} must use YYYYMMDDTHHMMSS or YYYYMMDDTHHMMSSZ"
    )


def _format_datetime(value):
    if value.tzinfo is not None:
        return value.strftime("%Y%m%dT%H%M%SZ")
    return value.strftime("%Y%m%dT%H%M%S")


def _parse_rule(value):
    if not isinstance(value, str) or not value:
        raise ValueError("rrule must be a non-empty string")

    if value != value.strip():
        raise ValueError("rrule cannot contain surrounding whitespace")

    if value.upper().startswith("RRULE:"):
        value = value[6:]

    if not value:
        raise ValueError("rrule cannot be empty")

    allowed = {"FREQ", "INTERVAL", "COUNT", "UNTIL"}
    parts = {}

    for component in value.split(";"):
        if component.count("=") != 1:
            raise ValueError(f"invalid RRULE component: {component!r}")

        key, raw = component.split("=", 1)
        key = key.upper()
        raw = raw.upper()

        if key not in allowed:
            raise ValueError(f"unsupported RRULE part: {key}")

        if key in parts:
            raise ValueError(f"duplicate RRULE part: {key}")

        if not raw:
            raise ValueError(f"empty RRULE value: {key}")

        parts[key] = raw

    if parts.get("FREQ") != "DAILY":
        raise ValueError("only FREQ=DAILY is supported")

    if "COUNT" in parts and "UNTIL" in parts:
        raise ValueError("COUNT and UNTIL cannot be used together")

    interval = 1
    if "INTERVAL" in parts:
        raw = parts["INTERVAL"]
        if not raw.isascii() or not raw.isdigit():
            raise ValueError("INTERVAL must be a positive integer")
        interval = int(raw)
        if interval < 1:
            raise ValueError("INTERVAL must be a positive integer")

    count = None
    if "COUNT" in parts:
        raw = parts["COUNT"]
        if not raw.isascii() or not raw.isdigit():
            raise ValueError("COUNT must be a positive integer")
        count = int(raw)
        if count < 1:
            raise ValueError("COUNT must be a positive integer")

    until = None
    if "UNTIL" in parts:
        until = _parse_datetime(parts["UNTIL"], "UNTIL")

    normalized = "FREQ=DAILY"

    if interval != 1:
        normalized += f";INTERVAL={interval}"

    if count is not None:
        normalized += f";COUNT={count}"

    if until is not None:
        normalized += f";UNTIL={_format_datetime(until)}"

    return interval, count, until, normalized


def _derive(inputs):
    start = _parse_datetime(inputs["dtstart"], "dtstart")
    lower = _parse_datetime(inputs["window_start"], "window_start")
    upper = _parse_datetime(inputs["window_end"], "window_end")

    if (start.tzinfo is None) != (lower.tzinfo is None):
        raise ValueError("window_start timezone mode must match DTSTART")

    if (start.tzinfo is None) != (upper.tzinfo is None):
        raise ValueError("window_end timezone mode must match DTSTART")

    if lower > upper:
        raise ValueError("window_start must not be after window_end")

    interval, count, until, normalized = _parse_rule(inputs["rrule"])

    if until is not None and ((start.tzinfo is None) != (until.tzinfo is None)):
        raise ValueError("UNTIL timezone mode must match DTSTART")

    limit = inputs["max_occurrences"]

    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("max_occurrences must be an integer")

    if not 1 <= limit <= 1000:
        raise ValueError("max_occurrences must be between 1 and 1000")

    occurrences = []
    truncated = False
    current = start
    generated = 0

    while current <= upper:
        if until is not None and current > until:
            break

        if count is not None and generated >= count:
            break

        generated += 1

        if current >= lower:
            if len(occurrences) < limit:
                occurrences.append(_format_datetime(current))
            else:
                truncated = True
                break

        try:
            current += timedelta(days=interval)
        except OverflowError:
            break

    return {
        "occurrences": occurrences,
        "total_count": len(occurrences),
        "truncated": truncated,
        "normalized_rrule": normalized,
    }


def verify_input(tool, inputs):
    if tool != Tool.EXPAND_RRULE and tool != Tool.EXPAND_RRULE.value:
        return "unknown tool"

    if not isinstance(inputs, dict):
        return "inputs must be a dictionary"

    required = (
        "dtstart",
        "rrule",
        "window_start",
        "window_end",
        "max_occurrences",
    )

    for name in required:
        if name not in inputs:
            return f"missing input field: {name}"

    for name in ("dtstart", "rrule", "window_start", "window_end"):
        if not isinstance(inputs[name], str):
            return f"{name} must be a string"

    if isinstance(inputs["max_occurrences"], bool):
        return "max_occurrences must be an integer"

    if not isinstance(inputs["max_occurrences"], int):
        return "max_occurrences must be an integer"

    try:
        _derive(inputs)
    except (ValueError, OverflowError) as exc:
        return str(exc)

    return None


def verify_output(tool, inputs, output, ctx):
    if tool != Tool.EXPAND_RRULE and tool != Tool.EXPAND_RRULE.value:
        return "unknown tool"

    problem = verify_input(tool, inputs)
    if problem is not None:
        return f"invalid input: {problem}"

    if not isinstance(output, dict):
        return "output must be a dictionary"

    required = (
        "occurrences",
        "total_count",
        "truncated",
        "normalized_rrule",
    )

    for name in required:
        if name not in output:
            return f"missing field: {name}"

    if not isinstance(output["occurrences"], list):
        return "occurrences must be a list"

    if any(not isinstance(item, str) for item in output["occurrences"]):
        return "occurrences must contain only strings"

    if isinstance(output["total_count"], bool) or not isinstance(output["total_count"], int):
        return "total_count must be an integer"

    if not isinstance(output["truncated"], bool):
        return "truncated must be a boolean"

    if not isinstance(output["normalized_rrule"], str):
        return "normalized_rrule must be a string"

    expected = _derive(inputs)

    checks = (
        ("occurrences", expected["occurrences"], output["occurrences"]),
        ("total_count", expected["total_count"], output["total_count"]),
        ("truncated", expected["truncated"], output["truncated"]),
        ("normalized_rrule", expected["normalized_rrule"], output["normalized_rrule"]),
    )

    for field, exp, act in checks:
        if exp != act:
            return f"{field}: expected {exp!r}, got {act!r}"

    return None


def verify_task(task, tools, inputs, output, ctx):
    if task != Task.EXPAND_RRULE and task != Task.EXPAND_RRULE.value:
        return "unknown task"

    if task not in TASKS and task != Task.EXPAND_RRULE.value:
        return "task is not registered"

    if isinstance(tools, str):
        supplied_tools = {tools}
    else:
        try:
            supplied_tools = set(tools)
        except TypeError:
            return "tools must be a string or iterable"

    if Tool.EXPAND_RRULE not in supplied_tools and Tool.EXPAND_RRULE.value not in supplied_tools:
        return "required tool expand_rrule is missing"

    return verify_output(Tool.EXPAND_RRULE, inputs, output, ctx)