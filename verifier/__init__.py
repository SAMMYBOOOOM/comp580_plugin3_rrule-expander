from contract import TASKS, TOOLS, Task, Tool

_MONTH_DAYS = (0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
_ALLOWED_PARTS = ("FREQ", "INTERVAL", "COUNT", "UNTIL")


def _is_leap(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def _days_in_month(y, m):
    if m == 2 and _is_leap(y):
        return 29
    return _MONTH_DAYS[m]


def _all_digits(s):
    if not s:
        return False
    for c in s:
        if c < "0" or c > "9":
            return False
    return True


def _parse_dt(value, field):
    generic = f"{field} must use YYYYMMDDTHHMMSS or YYYYMMDDTHHMMSSZ"
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    if len(value) == 16 and value[15] == "Z":
        body = value[:15]
        tz = True
    elif len(value) == 15:
        body = value
        tz = False
    else:
        raise ValueError(generic)
    if body[8] != "T":
        raise ValueError(generic)
    chunks = (body[0:4], body[4:6], body[6:8], body[9:11], body[11:13], body[13:15])
    for chunk in chunks:
        if not _all_digits(chunk):
            raise ValueError(generic)
    y = int(chunks[0]); mo = int(chunks[1]); d = int(chunks[2])
    h = int(chunks[3]); mi = int(chunks[4]); s = int(chunks[5])
    if not (1 <= y <= 9999):
        raise ValueError(generic)
    if not (1 <= mo <= 12):
        raise ValueError(generic)
    if not (1 <= d <= _days_in_month(y, mo)):
        raise ValueError(generic)
    if not (0 <= h <= 23) or not (0 <= mi <= 59) or not (0 <= s <= 59):
        raise ValueError(generic)
    return (y, mo, d, h, mi, s, tz)


def _format_dt(dt):
    y, mo, d, h, mi, s, tz = dt
    body = f"{y:04d}{mo:02d}{d:02d}T{h:02d}{mi:02d}{s:02d}"
    if tz:
        return body + "Z"
    return body


def _cmp_dt(a, b):
    ak = a[:6]
    bk = b[:6]
    if ak < bk:
        return -1
    if ak > bk:
        return 1
    return 0


def _add_days(dt, n):
    y, mo, d, h, mi, s, tz = dt
    if n > (9999 - y + 1) * 366:
        return None
    d += n
    while True:
        if y > 9999:
            return None
        dim = _days_in_month(y, mo)
        if d <= dim:
            return (y, mo, d, h, mi, s, tz)
        d -= dim
        mo += 1
        if mo > 12:
            mo = 1
            y += 1


def _parse_rrule(value):
    if not isinstance(value, str) or not value:
        raise ValueError("rrule must be a non-empty string")
    if value != value.strip():
        raise ValueError("rrule cannot contain surrounding whitespace")
    if value.upper().startswith("RRULE:"):
        value = value[6:]
    if not value:
        raise ValueError("rrule cannot be empty")
    parts = {}
    for component in value.split(";"):
        if component.count("=") != 1:
            raise ValueError(f"invalid RRULE component: {component!r}")
        key, raw = component.split("=", 1)
        key = key.upper()
        raw = raw.upper()
        if key not in _ALLOWED_PARTS:
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
        if not _all_digits(raw):
            raise ValueError("INTERVAL must be a positive integer")
        interval = int(raw)
        if interval < 1:
            raise ValueError("INTERVAL must be a positive integer")
    count = None
    if "COUNT" in parts:
        raw = parts["COUNT"]
        if not _all_digits(raw):
            raise ValueError("COUNT must be a positive integer")
        count = int(raw)
        if count < 1:
            raise ValueError("COUNT must be a positive integer")
    until = None
    if "UNTIL" in parts:
        until = _parse_dt(parts["UNTIL"], "UNTIL")
    normalized = "FREQ=DAILY"
    if interval != 1:
        normalized += f";INTERVAL={interval}"
    if count is not None:
        normalized += f";COUNT={count}"
    if until is not None:
        normalized += f";UNTIL={_format_dt(until)}"
    return interval, count, until, normalized


def _expand(dtstart, rrule, window_start, window_end, max_occurrences):
    start = _parse_dt(dtstart, "dtstart")
    lower = _parse_dt(window_start, "window_start")
    upper = _parse_dt(window_end, "window_end")
    if start[6] != lower[6]:
        raise ValueError("window_start timezone mode must match DTSTART")
    if start[6] != upper[6]:
        raise ValueError("window_end timezone mode must match DTSTART")
    if _cmp_dt(lower, upper) > 0:
        raise ValueError("window_start must not be after window_end")
    interval, count, until, normalized = _parse_rrule(rrule)
    if until is not None and start[6] != until[6]:
        raise ValueError("UNTIL timezone mode must match DTSTART")
    if isinstance(max_occurrences, bool) or not isinstance(max_occurrences, int):
        raise ValueError("max_occurrences must be an integer")
    if not 1 <= max_occurrences <= 1000:
        raise ValueError("max_occurrences must be between 1 and 1000")
    occurrences = []
    truncated = False
    current = start
    generated = 0
    while _cmp_dt(current, upper) <= 0:
        if until is not None and _cmp_dt(current, until) > 0:
            break
        if count is not None and generated >= count:
            break
        generated += 1
        if _cmp_dt(current, lower) >= 0:
            if len(occurrences) < max_occurrences:
                occurrences.append(_format_dt(current))
            else:
                truncated = True
                break
        nxt = _add_days(current, interval)
        if nxt is None:
            break
        current = nxt
    return {
        "occurrences": occurrences,
        "total_count": len(occurrences),
        "truncated": truncated,
        "normalized_rrule": normalized,
    }


def _required_fields(tool):
    if tool == Tool.EXPAND_RRULE:
        return ("dtstart", "rrule", "window_start", "window_end", "max_occurrences")
    return None


def _check_common_inputs(tool, inputs):
    required = _required_fields(tool)
    if required is None:
        return "unknown tool"
    if not isinstance(inputs, dict):
        return "inputs must be a dictionary"
    for f in required:
        if f not in inputs:
            return f"missing input field: {f}"
    if not isinstance(inputs["dtstart"], str):
        return "dtstart must be a string"
    if not isinstance(inputs["rrule"], str):
        return "rrule must be a string"
    if not isinstance(inputs["window_start"], str):
        return "window_start must be a string"
    if not isinstance(inputs["window_end"], str):
        return "window_end must be a string"
    mo = inputs["max_occurrences"]
    if isinstance(mo, bool) or not isinstance(mo, int):
        return "max_occurrences must be an integer"
    return None


def verify_input(tool, inputs):
    problem = _check_common_inputs(tool, inputs)
    if problem is not None:
        return problem
    try:
        _expand(
            inputs["dtstart"],
            inputs["rrule"],
            inputs["window_start"],
            inputs["window_end"],
            inputs["max_occurrences"],
        )
    except ValueError as e:
        return str(e)
    return None


def _compare_output(expected, output):
    if not isinstance(output, dict):
        return "output must be a dictionary"
    for field in ("occurrences", "total_count", "truncated", "normalized_rrule"):
        if field not in output:
            return f"missing field: {field}"
    occ = output["occurrences"]
    if not isinstance(occ, list):
        return "occurrences must be a list"
    for o in occ:
        if not isinstance(o, str):
            return "occurrences must contain only strings"
    if isinstance(output["total_count"], bool) or not isinstance(output["total_count"], int):
        return "total_count must be an integer"
    if not isinstance(output["truncated"], bool):
        return "truncated must be a boolean"
    if not isinstance(output["normalized_rrule"], str):
        return "normalized_rrule must be a string"
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


def verify_output(tool, inputs, output, ctx):
    problem = _check_common_inputs(tool, inputs)
    if problem is not None:
        return problem
    try:
        expected = _expand(
            inputs["dtstart"],
            inputs["rrule"],
            inputs["window_start"],
            inputs["window_end"],
            inputs["max_occurrences"],
        )
    except ValueError as e:
        return str(e)
    return _compare_output(expected, output)


def verify_task(task, tools, inputs, output, ctx):
    if task not in TASKS:
        return "unknown task"
    if isinstance(tools, str):
        tool_list = [tools]
    else:
        try:
            tool_list = list(tools)
        except TypeError:
            return "tools must be a string or iterable"
    if "expand_rrule" not in tool_list:
        return "required tool expand_rrule is missing"
    return verify_output(Tool.EXPAND_RRULE, inputs, output, ctx)