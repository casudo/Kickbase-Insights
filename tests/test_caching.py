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


def test_battles_fetches_each_battle_type_once():
    """Every user asks for the same 5 battle standings; fetch each one once."""
    fake = use_fake({"/battles/": {"us": [{"u": {"i": "1"}, "v": 10}]}})

    ### 13 users each asking for battle types 8, 4, 5, 6, 7
    for _ in range(13):
        for battle_type in (8, 4, 5, 6, 7):
            leagues.battles("token", "league1", battle_type)

    assert len(fake.urls) == 5, f"expected 5 HTTP calls for 5 battle types, got {len(fake.urls)}"


def test_battles_keeps_battle_types_apart():
    fake = use_fake({"/battles/": {"us": []}})

    leagues.battles("token", "league1", 4)
    leagues.battles("token", "league1", 5)

    assert len(fake.urls) == 2, f"expected 2 HTTP calls for 2 battle types, got {len(fake.urls)}"


def test_user_stats_fetches_each_user_once():
    """balances() and league_user_stats_tables() both ask for every user."""
    fake = use_fake({"/managers/": {"tv": 1, "pl": 1}})

    leagues.user_stats("token", "league1", "user1")
    leagues.user_stats("token", "league1", "user1")

    assert len(fake.urls) == 1, f"expected 1 HTTP call, got {len(fake.urls)}"


def test_user_stats_keeps_users_apart():
    fake = use_fake({"/managers/": {"tv": 1}})

    leagues.user_stats("token", "league1", "user1")
    leagues.user_stats("token", "league1", "user2")

    assert len(fake.urls) == 2, f"expected 2 HTTP calls for 2 users, got {len(fake.urls)}"


def test_profile_picture_is_downloaded_once_per_user():
    """Each call downloads a full JPEG, and both functions ask for every user."""
    from backend import miscellaneous

    class ImageResponse:
        status_code = 200
        url = "https://cdn.kickbase.com/files/users/1/0"

    class CountingCdn:
        def __init__(self):
            self.urls = []

        def get(self, url, headers=None, timeout=None):
            self.urls.append(url)
            return ImageResponse()

    cdn = CountingCdn()
    original = miscellaneous.requests
    miscellaneous.requests = cdn
    try:
        miscellaneous.clear_caches()
        miscellaneous.get_profilepic("user1")
        miscellaneous.get_profilepic("user1")
        count = len(cdn.urls)
    finally:
        miscellaneous.requests = original

    assert count == 1, f"expected 1 image download, got {count}"


def test_prefetch_players_fills_both_caches():
    fake = use_fake({"/marketValue/": {"it": [{"mv": 1}]}, "/players/": {"i": "x"}})

    leagues.prefetch_players("token", "league1", ["1", "2", "3"])

    ### one statistics call and one market value call per player
    assert len(fake.urls) == 6, f"expected 6 HTTP calls, got {len(fake.urls)}: {fake.urls}"


def test_prefetch_players_makes_later_lookups_free():
    fake = use_fake({"/marketValue/": {"it": [{"mv": 1}]}, "/players/": {"i": "x"}})

    leagues.prefetch_players("token", "league1", ["1", "2"])
    after_prefetch = len(fake.urls)
    leagues.player_statistics("token", "league1", "1")
    leagues.player_marketvalue("token", "1")

    assert len(fake.urls) == after_prefetch, \
        f"lookups after prefetch hit the network: {after_prefetch} -> {len(fake.urls)}"


def test_prefetch_players_skips_what_is_cached():
    fake = use_fake({"/marketValue/": {"it": [{"mv": 1}]}, "/players/": {"i": "x"}})

    leagues.player_statistics("token", "league1", "1")
    before = len(fake.urls)
    leagues.prefetch_players("token", "league1", ["1"])

    ### only the market value is still missing for player 1
    assert len(fake.urls) == before + 1, \
        f"expected 1 further call, got {len(fake.urls) - before}"


def test_prefetch_players_runs_concurrently():
    """463 players at ~90ms each must not be fetched one after another."""
    import time

    delay = 0.05
    players = [str(i) for i in range(16)]

    fake = use_fake({})

    def slow(url, headers=None, timeout=None):
        fake.urls.append(url)
        time.sleep(delay)
        return FakeResponse({"it": [{"mv": 1}], "i": "x"})

    fake.get = slow

    start = time.time()
    leagues.prefetch_players("token", "league1", players)
    elapsed = time.time() - start

    sequential = delay * len(players) * 2  # statistics + market value each
    assert elapsed < sequential / 3, \
        f"took {elapsed:.2f}s, sequential would be {sequential:.2f}s - not concurrent"


def test_prefetch_players_handles_an_empty_list():
    fake = use_fake({})
    leagues.prefetch_players("token", "league1", [])
    assert len(fake.urls) == 0, "an empty list should make no requests"


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
    check("battles fetches each battle type once", test_battles_fetches_each_battle_type_once)
    check("battles keeps battle types apart", test_battles_keeps_battle_types_apart)
    check("user_stats fetches each user once", test_user_stats_fetches_each_user_once)
    check("user_stats keeps users apart", test_user_stats_keeps_users_apart)
    check("profile picture downloaded once per user", test_profile_picture_is_downloaded_once_per_user)

    print("\nprefetch_players()")
    check("fills both caches", test_prefetch_players_fills_both_caches)
    check("makes later lookups free", test_prefetch_players_makes_later_lookups_free)
    check("skips what is cached", test_prefetch_players_skips_what_is_cached)
    check("runs concurrently", test_prefetch_players_runs_concurrently)
    check("handles an empty list", test_prefetch_players_handles_an_empty_list)
    check("clear_caches forces a refetch", test_clear_caches_forces_a_refetch)

    leagues.requests = real_requests

    total, passed = len(PASSED), sum(PASSED)
    print(f"\n{passed}/{total} passed")
    sys.exit(0 if passed == total else 1)
