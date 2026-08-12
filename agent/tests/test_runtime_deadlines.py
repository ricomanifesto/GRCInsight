from core.runtime import deadline_from_unix_ms, earliest_deadline


def test_deadline_from_unix_ms_reserves_caller_completion_time():
    deadline = deadline_from_unix_ms(
        400_000,
        monotonic_clock=lambda: 100.0,
        wall_clock=lambda: 100.0,
    )

    assert deadline == 370.0


def test_deadline_from_unix_ms_expires_before_the_caller():
    deadline = deadline_from_unix_ms(
        120_000,
        monotonic_clock=lambda: 100.0,
        wall_clock=lambda: 100.0,
    )

    assert deadline == 100.0


def test_earliest_deadline_keeps_the_tightest_runtime_limit():
    assert earliest_deadline(None, 700.0, 370.0) == 370.0
    assert earliest_deadline(None, None) is None
