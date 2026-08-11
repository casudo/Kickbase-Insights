"""Tests for START_DATE as an ISO 8601 league reset timestamp.

Dependency free on purpose: the project has no test framework, so this runs with
the project venv directly and needs no extra packages.

    ./venv/bin/python tests/test_start_date.py
"""

import sys

from datetime import datetime, timezone
from os import environ, path

### Make the repository root importable regardless of where this is run from
sys.path.insert(0, path.dirname(path.dirname(path.abspath(__file__))))

from backend import exceptions, miscellaneous

### ===============================================================================

PASSED = []


def check(name, fn):
    """Run a single test and record the result."""
    try:
        fn()
    except AssertionError as e:
        print(f"  FAIL  {name}\n        {e}")
        PASSED.append(False)
    except Exception as e:
        print(f"  ERROR {name}\n        {type(e).__name__}: {e}")
        PASSED.append(False)
    else:
        print(f"  ok    {name}")
        PASSED.append(True)


def set_start_date(value):
    """Set or clear the START_DATE environment variable."""
    if value is None:
        environ.pop("START_DATE", None)
    else:
        environ["START_DATE"] = value


### ===============================================================================
### get_start_datetime()
### ===============================================================================


def test_parses_iso_utc_timestamp():
    set_start_date("2026-08-01T18:00:00Z")
    result = miscellaneous.get_start_datetime()
    expected = datetime(2026, 8, 1, 18, 0, 0, tzinfo=timezone.utc)
    assert result == expected, f"expected {expected}, got {result}"


def test_parsed_timestamp_is_timezone_aware():
    set_start_date("2026-08-01T18:00:00Z")
    result = miscellaneous.get_start_datetime()
    assert result.tzinfo is not None, "expected an aware datetime, got a naive one"


def test_non_utc_offset_is_converted_to_utc():
    ### 20:00 in Berlin (+02:00) is 18:00 UTC
    set_start_date("2026-08-01T20:00:00+02:00")
    result = miscellaneous.get_start_datetime()
    expected = datetime(2026, 8, 1, 18, 0, 0, tzinfo=timezone.utc)
    assert result == expected, f"expected {expected}, got {result}"


def test_rejects_old_german_date_format():
    set_start_date("01.08.2026")
    try:
        miscellaneous.get_start_datetime()
    except exceptions.KickbaseException as e:
        assert "01.08.2026" in str(e), f"error should name the bad value, got: {e}"
        assert "ISO 8601" in str(e), f"error should point at ISO 8601, got: {e}"
    else:
        raise AssertionError("expected a KickbaseException for the old dd.mm.yyyy format")


def test_rejects_timestamp_without_offset():
    ### Without an offset there is no way to know whether this is UTC or local time
    set_start_date("2026-08-01T18:00:00")
    try:
        miscellaneous.get_start_datetime()
    except exceptions.KickbaseException as e:
        assert "offset" in str(e).lower() or "utc" in str(e).lower(), \
            f"error should explain the missing offset, got: {e}"
    else:
        raise AssertionError("expected a KickbaseException for a naive timestamp")


def test_rejects_missing_value():
    set_start_date(None)
    try:
        miscellaneous.get_start_datetime()
    except exceptions.KickbaseException as e:
        assert "START_DATE" in str(e), f"error should name the variable, got: {e}"
    else:
        raise AssertionError("expected a KickbaseException when START_DATE is unset")


def test_rejects_empty_value():
    set_start_date("")
    try:
        miscellaneous.get_start_datetime()
    except exceptions.KickbaseException:
        pass
    else:
        raise AssertionError("expected a KickbaseException when START_DATE is empty")


### ===============================================================================
### filter_transfers_from()
### ===============================================================================

CUTOFF = datetime(2026, 8, 1, 18, 0, 0, tzinfo=timezone.utc)


def transfer(dt, tid="x"):
    """Build a minimal activity feed item."""
    return {"i": tid, "t": 15, "dt": dt, "data": {"pi": "1", "trp": 1}}


def test_drops_events_before_the_cutoff():
    ### These are the four real pre-reset events from the affected league
    items = [
        transfer("2026-08-01T16:43:17Z", "a"),
        transfer("2026-08-01T17:12:08Z", "b"),
        transfer("2026-08-01T17:47:34Z", "c"),
        transfer("2026-08-01T17:47:43Z", "d"),
    ]
    result = miscellaneous.filter_transfers_from(items, CUTOFF)
    assert result == [], f"expected all pre-cutoff events dropped, got {result}"


def test_keeps_events_after_the_cutoff():
    items = [transfer("2026-08-01T18:10:57Z", "a"), transfer("2026-08-11T20:18:51Z", "b")]
    result = miscellaneous.filter_transfers_from(items, CUTOFF)
    assert len(result) == 2, f"expected both post-cutoff events kept, got {result}"


def test_keeps_event_exactly_on_the_cutoff():
    ### The boundary is inclusive
    items = [transfer("2026-08-01T18:00:00Z", "a")]
    result = miscellaneous.filter_transfers_from(items, CUTOFF)
    assert len(result) == 1, f"expected the boundary event kept, got {result}"


def test_keeps_order_and_drops_only_the_old_ones():
    items = [
        transfer("2026-08-01T16:43:17Z", "old"),
        transfer("2026-08-01T18:10:57Z", "new1"),
        transfer("2026-08-02T09:00:00Z", "new2"),
    ]
    result = miscellaneous.filter_transfers_from(items, CUTOFF)
    assert [i["i"] for i in result] == ["new1", "new2"], f"got {[i['i'] for i in result]}"


def test_handles_an_empty_list():
    assert miscellaneous.filter_transfers_from([], CUTOFF) == []


### ===============================================================================
### turnovers() writes a cleaned cache
### ===============================================================================


def test_turnovers_cleans_pre_cutoff_events_from_the_cache():
    """A cache holding pre-reset events is repaired on the next run."""
    import json
    import tempfile

    import main
    from backend.kickbase.v4 import leagues

    with tempfile.TemporaryDirectory() as tmp:
        data_dir = path.join(tmp, "data")
        ts_dir = path.join(data_dir, "timestamps")

        ### Point every writer at the temporary directory
        original = (main.DATA_DIR, miscellaneous.DATA_DIR, miscellaneous.TIMESTAMP_DIR,
                    leagues.transfers, leagues.player_statistics,
                    leagues.player_marketvalue, miscellaneous.calculate_revenue_data_daily)
        main.DATA_DIR = data_dir
        miscellaneous.DATA_DIR = data_dir
        miscellaneous.TIMESTAMP_DIR = ts_dir

        try:
            ### A stale cache with one pre-reset and one post-reset event
            from os import makedirs
            makedirs(ts_dir, exist_ok=True)
            with open(path.join(data_dir, "all_transfers.json"), "w") as f:
                json.dump([
                    {"i": "old", "t": 15, "dt": "2026-08-01T16:43:17Z",
                     "data": {"slr": "A", "pi": "1", "tid": "1", "trp": 100}},
                    {"i": "new", "t": 15, "dt": "2026-08-01T18:20:27Z",
                     "data": {"slr": "A", "pi": "2", "tid": "1", "trp": 200}},
                ], f)

            set_start_date("2026-08-01T18:00:00Z")
            leagues.transfers = lambda token, lid: []
            leagues.player_statistics = lambda token, lid, pid: {"fn": "F", "ln": "L"}
            leagues.player_marketvalue = lambda token, pid: []
            miscellaneous.calculate_revenue_data_daily = lambda t: None

            class FakeLeague:
                id = "1"
                name = "Test"

            main.turnovers("token", FakeLeague())

            with open(path.join(data_dir, "all_transfers.json")) as f:
                cache = json.load(f)
        finally:
            (main.DATA_DIR, miscellaneous.DATA_DIR, miscellaneous.TIMESTAMP_DIR,
             leagues.transfers, leagues.player_statistics,
             leagues.player_marketvalue, miscellaneous.calculate_revenue_data_daily) = original

    ids = [i["i"] for i in cache]
    assert ids == ["new"], f"expected the pre-cutoff event purged from the cache, got {ids}"


### ===============================================================================
### calculate_revenue_data_daily()
### ===============================================================================


def test_revenue_graph_accepts_an_iso_start_date():
    """The revenue graph anchors its start point at START_DATE."""
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        data_dir = path.join(tmp, "data")
        ts_dir = path.join(data_dir, "timestamps")
        from os import makedirs
        makedirs(ts_dir, exist_ok=True)

        with open(path.join(data_dir, "STATIC_users.json"), "w") as f:
            json.dump({"u1": "UserA"}, f)

        original = (miscellaneous.DATA_DIR, miscellaneous.TIMESTAMP_DIR)
        miscellaneous.DATA_DIR = data_dir
        miscellaneous.TIMESTAMP_DIR = ts_dir

        try:
            set_start_date("2026-08-01T18:00:00Z")
            turnovers = [(
                {"user": "UserA", "price": 1_000_000, "date": "2026-08-01T18:00:00+00:00"},
                {"user": "UserA", "price": 1_500_000, "date": "2026-08-05T12:00:00Z"},
            )]
            miscellaneous.calculate_revenue_data_daily(turnovers)

            with open(path.join(data_dir, "revenue_sum.json")) as f:
                result = json.load(f)
        finally:
            miscellaneous.DATA_DIR, miscellaneous.TIMESTAMP_DIR = original

    assert "UserA" in result, f"expected a series for UserA, got {result}"
    assert len(result["UserA"]) > 0, "expected at least one data point"
    ### Each point is (date, cumulative revenue). The series must start at the cutoff
    ### date and pick up the 500k profit on the day of the sale.
    assert result["UserA"][0][0] == "2026-08-01", \
        f"expected the series to start on the START_DATE day, got {result['UserA'][0]}"
    assert any(point[1] == 500_000 for point in result["UserA"]), \
        f"expected the 500000 revenue in the series, got {result['UserA']}"


### ===============================================================================

if __name__ == "__main__":
    print("get_start_datetime()")
    check("parses an ISO UTC timestamp", test_parses_iso_utc_timestamp)
    check("returns an aware datetime", test_parsed_timestamp_is_timezone_aware)
    check("converts a non-UTC offset to UTC", test_non_utc_offset_is_converted_to_utc)
    check("rejects the old dd.mm.yyyy format", test_rejects_old_german_date_format)
    check("rejects a timestamp without an offset", test_rejects_timestamp_without_offset)
    check("rejects a missing value", test_rejects_missing_value)
    check("rejects an empty value", test_rejects_empty_value)

    print("\nfilter_transfers_from()")
    check("drops events before the cutoff", test_drops_events_before_the_cutoff)
    check("keeps events after the cutoff", test_keeps_events_after_the_cutoff)
    check("keeps an event exactly on the cutoff", test_keeps_event_exactly_on_the_cutoff)
    check("keeps order and drops only old events", test_keeps_order_and_drops_only_the_old_ones)
    check("handles an empty list", test_handles_an_empty_list)

    print("\nturnovers()")
    check("cleans pre-cutoff events from the cache",
          test_turnovers_cleans_pre_cutoff_events_from_the_cache)

    print("\ncalculate_revenue_data_daily()")
    check("accepts an ISO START_DATE", test_revenue_graph_accepts_an_iso_start_date)

    total, passed = len(PASSED), sum(PASSED)
    print(f"\n{passed}/{total} passed")
    sys.exit(0 if passed == total else 1)
