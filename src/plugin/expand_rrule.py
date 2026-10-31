from datetime import datetime, timedelta

from contract import ExpandInput, ExpandOutput


_ALLOWED_PARTS = {"FREQ", "INTERVAL", "COUNT", "UNTIL"}


def _parse_datetime(value: str, field: str) -> datetime:
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
                from datetime import timezone
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            continue

    raise ValueError(
        f"{field} must use YYYYMMDDTHHMMSS or YYYYMMDDTHHMMSSZ"
    )


def _format_datetime(value: datetime) -> str:
    if value.tzinfo is not None:
        return value.strftime("%Y%m%dT%H%M%SZ")
    return value.strftime("%Y%m%dT%H%M%S")


def _parse_rrule(value: str) -> tuple[int, int | None, datetime | None, str]:
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

        key, raw_value = component.split("=", 1)
        key = key.upper()
        raw_value = raw_value.upper()

        if key not in _ALLOWED_PARTS:
            raise ValueError(f"unsupported RRULE part: {key}")

        if key in parts:
            raise ValueError(f"duplicate RRULE part: {key}")

        if not raw_value:
            raise ValueError(f"empty RRULE value: {key}")

        parts[key] = raw_value

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

    normalized = f"FREQ=DAILY"
    if interval != 1:
        normalized += f";INTERVAL={interval}"
    if count is not None:
        normalized += f";COUNT={count}"
    if until is not None:
        normalized += f";UNTIL={_format_datetime(until)}"

    return interval, count, until, normalized


def _expand(
    dtstart: str,
    rrule: str,
    window_start: str,
    window_end: str,
    max_occurrences: int,
) -> dict:
    start = _parse_datetime(dtstart, "dtstart")
    lower = _parse_datetime(window_start, "window_start")
    upper = _parse_datetime(window_end, "window_end")

    if (start.tzinfo is None) != (lower.tzinfo is None):
        raise ValueError("window_start timezone mode must match DTSTART")

    if (start.tzinfo is None) != (upper.tzinfo is None):
        raise ValueError("window_end timezone mode must match DTSTART")

    if lower > upper:
        raise ValueError("window_start must not be after window_end")

    interval, count, until, normalized = _parse_rrule(rrule)

    if until is not None and ((start.tzinfo is None) != (until.tzinfo is None)):
        raise ValueError("UNTIL timezone mode must match DTSTART")

    if isinstance(max_occurrences, bool) or not isinstance(max_occurrences, int):
        raise ValueError("max_occurrences must be an integer")

    if not 1 <= max_occurrences <= 1000:
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
            if len(occurrences) < max_occurrences:
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


def expand_rrule(
    dtstart: str,
    rrule: str,
    window_start: str,
    window_end: str,
    max_occurrences: int = 100,
) -> dict:
    """Validate and expand a supported RFC 5545 daily recurrence rule."""
    inputs = ExpandInput(
        dtstart=dtstart,
        rrule=rrule,
        window_start=window_start,
        window_end=window_end,
        max_occurrences=max_occurrences,
    )

    result = _expand(
        inputs.dtstart,
        inputs.rrule,
        inputs.window_start,
        inputs.window_end,
        inputs.max_occurrences,
    )

    output = ExpandOutput(
        occurrences=result["occurrences"],
        total_count=result["total_count"],
        truncated=result["truncated"],
        normalized_rrule=result["normalized_rrule"],
    )

    return {
        "occurrences": output.occurrences,
        "total_count": output.total_count,
        "truncated": output.truncated,
        "normalized_rrule": output.normalized_rrule,
    }