from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated

from slimconfig import Output


class Tool(StrEnum):
    EXPAND_RRULE = "expand_rrule"


class Task(StrEnum):
    EXPAND_RRULE = "expand-rrule"


@dataclass
class ExpandInput(Output):
    dtstart: Annotated[
        str,
        "RFC 5545 DATE-TIME in basic format YYYYMMDDTHHMMSS or YYYYMMDDTHHMMSSZ. "
        "Floating and UTC date-times are supported; other timezone forms are rejected.",
    ]
    rrule: Annotated[
        str,
        "Strict RRULE string. Supported parts are FREQ=DAILY, INTERVAL, COUNT, and UNTIL. "
        "Parts are case-insensitive. Duplicate, unknown, and unsupported parts are rejected. "
        "COUNT and UNTIL cannot appear together.",
    ]
    window_start: Annotated[
        str,
        "Inclusive expansion-window start, in the same date-time form and timezone mode as DTSTART.",
    ]
    window_end: Annotated[
        str,
        "Inclusive expansion-window end, in the same date-time form and timezone mode as DTSTART.",
    ]
    max_occurrences: Annotated[
        int,
        "Maximum number of returned occurrences. Must be an integer from 1 through 1000; bool is rejected.",
    ]


@dataclass
class ExpandOutput(Output):
    occurrences: Annotated[
        list[str],
        "Ordered RFC 5545 basic DATE-TIME occurrence strings within the inclusive window.",
    ]
    total_count: Annotated[
        int,
        "Number of occurrences returned in this response.",
    ]
    truncated: Annotated[
        bool,
        "True when additional matching occurrences exist in the requested window beyond the output limit.",
    ]
    normalized_rrule: Annotated[
        str,
        "Canonical supported RRULE with FREQ first and optional INTERVAL, COUNT, or UNTIL afterward.",
    ]


TOOLS = {
    Tool.EXPAND_RRULE: (ExpandInput, ExpandOutput),
}

TASKS = {
    Task.EXPAND_RRULE: (ExpandInput, ExpandOutput),
}