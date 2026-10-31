import pytest

from plugin.expand_rrule import expand_rrule


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


def test_daily_expansion():
    result = expand_rrule(**base())

    assert result["occurrences"] == [
        "20261001T090000",
        "20261002T090000",
        "20261003T090000",
        "20261004T090000",
        "20261005T090000",
    ]
    assert result["total_count"] == 5
    assert result["truncated"] is False
    assert result["normalized_rrule"] == "FREQ=DAILY"


def test_interval_two():
    result = expand_rrule(**base(rrule="FREQ=DAILY;INTERVAL=2"))

    assert result["occurrences"] == [
        "20261001T090000",
        "20261003T090000",
        "20261005T090000",
    ]


def test_count_limits_occurrences_from_dtstart():
    result = expand_rrule(
        **base(
            rrule="FREQ=DAILY;COUNT=3",
            window_start="20261002T000000",
        )
    )

    assert result["occurrences"] == [
        "20261002T090000",
        "20261003T090000",
    ]


def test_until_is_inclusive():
    result = expand_rrule(
        **base(rrule="FREQ=DAILY;UNTIL=20261003T090000")
    )

    assert result["occurrences"] == [
        "20261001T090000",
        "20261002T090000",
        "20261003T090000",
    ]


def test_window_is_inclusive():
    result = expand_rrule(
        **base(
            window_start="20261002T090000",
            window_end="20261003T090000",
        )
    )

    assert result["occurrences"] == [
        "20261002T090000",
        "20261003T090000",
    ]


def test_empty_window_result():
    result = expand_rrule(
        **base(
            rrule="FREQ=DAILY;COUNT=5",
            window_start="20261010T000000",
            window_end="20261012T000000",
        )
    )

    assert result["occurrences"] == []
    assert result["total_count"] == 0
    assert result["truncated"] is False


def test_output_limit_and_truncation():
    result = expand_rrule(**base(max_occurrences=2))

    assert result["occurrences"] == [
        "20261001T090000",
        "20261002T090000",
    ]
    assert result["total_count"] == 2
    assert result["truncated"] is True


def test_rrule_prefix_and_case_normalization():
    result = expand_rrule(
        **base(rrule="rrule:freq=daily;interval=2")
    )

    assert result["normalized_rrule"] == "FREQ=DAILY;INTERVAL=2"


def test_utc_datetime():
    result = expand_rrule(
        dtstart="20261001T090000Z",
        rrule="FREQ=DAILY;COUNT=2",
        window_start="20261001T000000Z",
        window_end="20261003T000000Z",
    )

    assert result["occurrences"] == [
        "20261001T090000Z",
        "20261002T090000Z",
    ]


@pytest.mark.parametrize(
    "rule",
    [
        "",
        " ",
        "FREQ=WEEKLY",
        "FREQ=DAILY;FREQ=DAILY",
        "FREQ=DAILY;BYDAY=MO",
        "FREQ=DAILY;COUNT=2;UNTIL=20261003T090000",
        "FREQ=DAILY;INTERVAL=0",
        "FREQ=DAILY;COUNT=0",
        "FREQ=DAILY;INTERVAL=abc",
    ],
)
def test_rejects_unsupported_or_malformed_rules(rule):
    with pytest.raises(ValueError):
        expand_rrule(**base(rrule=rule))


def test_rejects_empty_dtstart():
    with pytest.raises(ValueError):
        expand_rrule(**base(dtstart=""))


def test_rejects_whitespace_dtstart():
    with pytest.raises(ValueError):
        expand_rrule(**base(dtstart=" "))


def test_rejects_invalid_date():
    with pytest.raises(ValueError):
        expand_rrule(**base(dtstart="20260230T090000"))


def test_rejects_reversed_window():
    with pytest.raises(ValueError):
        expand_rrule(
            **base(
                window_start="20261005T000000",
                window_end="20261001T000000",
            )
        )


def test_rejects_mismatched_timezone_mode():
    with pytest.raises(ValueError):
        expand_rrule(
            **base(
                dtstart="20261001T090000Z",
                window_start="20261001T000000",
            )
        )


@pytest.mark.parametrize("limit", [0, -1, 1001, True, 1.5, "2"])
def test_rejects_invalid_output_limit(limit):
    with pytest.raises(ValueError):
        expand_rrule(**base(max_occurrences=limit))


def test_shortest_valid_interval():
    result = expand_rrule(
        **base(
            rrule="FREQ=DAILY;INTERVAL=1",
            window_end="20261001T235959",
        )
    )

    assert result["occurrences"] == ["20261001T090000"]
    assert result["normalized_rrule"] == "FREQ=DAILY"


def test_maximum_allowed_output_limit():
    result = expand_rrule(
        **base(
            window_end="20261001T235959",
            max_occurrences=1000,
        )
    )

    assert result["total_count"] == 1
    assert result["truncated"] is False


def test_until_timezone_mismatch():
    with pytest.raises(ValueError):
        expand_rrule(
            **base(rrule="FREQ=DAILY;UNTIL=20261003T090000Z")
        )


def test_rrule_with_surrounding_whitespace():
    with pytest.raises(ValueError):
        expand_rrule(**base(rrule=" FREQ=DAILY"))