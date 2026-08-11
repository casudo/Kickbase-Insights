"""Tests for per-run caching of repeated Kickbase API calls.

main.py walks every player twice, in market_value_changes() and in
taken_free_players(), and asks for the same player statistics both times. The
activity feed is paged through three separate times per run. None of that
changes between calls within a run, so it is fetched once and reused.

    ./venv/bin/python tests/test_caching.py
"""

import sys

from os import path

sys.path.insert(0, path.dirname(path.dirname(path.abspath(__file__))))

from backend.kickbase.v4 import leagues

### ===============================================================================

PASSED = []


def check(name, fn):
    try:
        leagues.clear_caches()
    except AttributeError:
        pass  # not implemented yet, the test itself will report it
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


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class CountingRequests:
    """Stands in for the requests module and records every GET."""

    def __init__(self, payloads):
        self.payloads = payloads
        self.urls = []

    def get(self, url, headers=None, timeout=None):
        self.urls.append(url)
        for fragment, payload in self.payloads.items():
            if fragment in url:
                return FakeResponse(payload)
        return FakeResponse({})


def use_fake(payloads):
    """Swap the requests module inside the leagues module."""
    fake = CountingRequests(payloads)
    leagues.requests = fake
    return fake


### ===============================================================================


def test_player_statistics_fetches_a_player_once():
    fake = use_fake({"/players/14300": {"i": "14300", "fn": "Paul"}})

    first = leagues.player_statistics("token", "league1", "14300")
    second = leagues.player_statistics("token", "league1", "14300")

    assert len(fake.urls) == 1, f"expected 1 HTTP call, got {len(fake.urls)}: {fake.urls}"
    assert first == second, "cached call returned different data"


def test_player_statistics_still_fetches_different_players():
    fake = use_fake({"/players/": {"i": "x"}})

    leagues.player_statistics("token", "league1", "14300")
    leagues.player_statistics("token", "league1", "173")

    assert len(fake.urls) == 2, f"expected 2 HTTP calls, got {len(fake.urls)}"


def test_player_statistics_is_scoped_per_league():
    """Ownership differs per league, so the league must be part of the key."""
    fake = use_fake({"/players/": {"i": "x"}})

    leagues.player_statistics("token", "league1", "14300")
    leagues.player_statistics("token", "league2", "14300")

    assert len(fake.urls) == 2, f"expected 2 HTTP calls for two leagues, got {len(fake.urls)}"


def test_player_marketvalue_fetches_a_player_once():
    fake = use_fake({"/marketValue/": {"it": [{"dt": 1, "mv": 100}]}})

    leagues.player_marketvalue("token", "14300")
    leagues.player_marketvalue("token", "14300")

    assert len(fake.urls) == 1, f"expected 1 HTTP call, got {len(fake.urls)}"


def test_transfers_pages_the_feed_once_per_league():
    """The feed is walked three times per run today; it must be walked once."""
    fake = use_fake({})
    ### First page has one item, second page is empty and ends the loop
    pages = [{"af": [{"i": "t1", "t": 15, "dt": "2026-08-05T10:00:00Z", "data": {}}]}, {"af": []}]
    calls = {"n": 0}

    def paged_get(url, headers=None, timeout=None):
        fake.urls.append(url)
        payload = pages[min(calls["n"], len(pages) - 1)]
        calls["n"] += 1
        return FakeResponse(payload)

    fake.get = paged_get

    first = leagues.transfers("token", "league1")
    calls_after_first = len(fake.urls)
    second = leagues.transfers("token", "league1")

    assert len(fake.urls) == calls_after_first, \
        f"second call re-paged the feed: {calls_after_first} -> {len(fake.urls)} HTTP calls"
    assert first == second, "cached feed returned different data"


def test_clear_caches_forces_a_refetch():
    fake = use_fake({"/players/14300": {"i": "14300"}})

    leagues.player_statistics("token", "league1", "14300")
    leagues.clear_caches()
    leagues.player_statistics("token", "league1", "14300")

    assert len(fake.urls) == 2, f"expected a refetch after clear_caches(), got {len(fake.urls)}"


### ===============================================================================

if __name__ == "__main__":
    import requests as real_requests

    print("caching")
    check("player_statistics fetches a player once", test_player_statistics_fetches_a_player_once)
    check("player_statistics still fetches different players", test_player_statistics_still_fetches_different_players)
    check("player_statistics is scoped per league", test_player_statistics_is_scoped_per_league)
    check("player_marketvalue fetches a player once", test_player_marketvalue_fetches_a_player_once)
    check("transfers pages the feed once per league", test_transfers_pages_the_feed_once_per_league)
    check("clear_caches forces a refetch", test_clear_caches_forces_a_refetch)

    leagues.requests = real_requests

    total, passed = len(PASSED), sum(PASSED)
    print(f"\n{passed}/{total} passed")
    sys.exit(0 if passed == total else 1)
