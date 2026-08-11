"""Tests for profile picture lookups.

The CDN takes about 20 seconds to answer for a user without a picture, measured
with both GET and HEAD, and it is not the body transfer: the same host answers a
normal request in 0.16s. With 13 managers that was 253 of the 259 seconds
balances() spent.

    ./venv/bin/python tests/test_profilepic.py
"""

import sys

from os import path

sys.path.insert(0, path.dirname(path.dirname(path.abspath(__file__))))

import requests as real_requests

from backend import exceptions, miscellaneous

### ===============================================================================

PASSED = []


def check(name, fn):
    miscellaneous.clear_caches()
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


class FakeCdn:
    """Stands in for the requests module."""

    exceptions = real_requests.exceptions

    def __init__(self, behaviour):
        self.behaviour = behaviour
        self.timeouts = []

    def get(self, url, headers=None, timeout=None):
        self.timeouts.append(timeout)
        return self.behaviour(url)


def with_cdn(behaviour, fn):
    fake = FakeCdn(behaviour)
    original = miscellaneous.requests
    miscellaneous.requests = fake
    try:
        return fn(), fake
    finally:
        miscellaneous.requests = original


class Response:
    def __init__(self, status_code, url="https://cdn.kickbase.com/files/users/1/0"):
        self.status_code = status_code
        self.url = url

    def raise_for_status(self):
        raise real_requests.exceptions.HTTPError(f"status {self.status_code}")


### ===============================================================================


def test_a_timeout_means_no_picture():
    """A slow CDN must not abort the whole run."""
    def times_out(url):
        raise real_requests.exceptions.ReadTimeout("too slow")

    result, _ = with_cdn(times_out, lambda: miscellaneous.get_profilepic("user1"))
    assert result is None, f"expected None on timeout, got {result!r}"


def test_a_timeout_is_actually_passed_to_the_request():
    """Without a timeout a single hung connection blocks the run forever."""
    _, fake = with_cdn(lambda url: Response(404), lambda: miscellaneous.get_profilepic("user1"))
    assert fake.timeouts, "no request was made"
    assert fake.timeouts[0] is not None, "the request was sent without a timeout"
    assert fake.timeouts[0] <= 10, f"timeout of {fake.timeouts[0]}s is too generous to help"


def test_missing_picture_returns_none():
    result, _ = with_cdn(lambda url: Response(404), lambda: miscellaneous.get_profilepic("user1"))
    assert result is None, f"expected None for a 404, got {result!r}"


def test_existing_picture_returns_its_url():
    url = "https://cdn.kickbase.com/files/users/42/0"
    result, _ = with_cdn(lambda u: Response(200, url), lambda: miscellaneous.get_profilepic("42"))
    assert result == url, f"expected {url}, got {result!r}"


def test_connection_error_still_raises():
    """A genuine network failure is not the same as a missing picture."""
    def refuses(url):
        raise real_requests.exceptions.ConnectionError("no route to host")

    try:
        with_cdn(refuses, lambda: miscellaneous.get_profilepic("user1"))
    except exceptions.NotificatonException:
        pass
    else:
        raise AssertionError("expected a NotificatonException for a connection error")


### ===============================================================================
### prefetch_profilepics()
### ===============================================================================


def test_prefetch_fills_the_cache_for_every_user():
    users = ["u1", "u2", "u3"]
    _, fake = with_cdn(lambda url: Response(404), lambda: miscellaneous.prefetch_profilepics(users))

    assert len(fake.timeouts) == 3, f"expected 3 lookups, got {len(fake.timeouts)}"
    for user_id in users:
        assert user_id in miscellaneous._profilepic_cache, f"{user_id} was not cached"


def test_prefetch_makes_later_lookups_free():
    users = ["u1", "u2"]

    fake = FakeCdn(lambda url: Response(404))
    original = miscellaneous.requests
    miscellaneous.requests = fake
    try:
        miscellaneous.prefetch_profilepics(users)
        after_prefetch = len(fake.timeouts)
        miscellaneous.get_profilepic("u1")
        miscellaneous.get_profilepic("u2")
        after_lookups = len(fake.timeouts)
    finally:
        miscellaneous.requests = original

    assert after_lookups == after_prefetch, \
        f"lookups after prefetch hit the network: {after_prefetch} -> {after_lookups}"


def test_prefetch_skips_users_already_cached():
    fake = FakeCdn(lambda url: Response(404))
    original = miscellaneous.requests
    miscellaneous.requests = fake
    try:
        miscellaneous.get_profilepic("u1")
        miscellaneous.prefetch_profilepics(["u1", "u2"])
        count = len(fake.timeouts)
    finally:
        miscellaneous.requests = original

    assert count == 2, f"expected 2 lookups total (u1 once, u2 once), got {count}"


def test_prefetch_runs_lookups_concurrently():
    """The whole point: 13 managers must not cost 13 timeouts back to back."""
    import time

    delay = 0.2
    users = [f"u{i}" for i in range(8)]

    def slow(url):
        time.sleep(delay)
        return Response(404)

    start = time.time()
    with_cdn(slow, lambda: miscellaneous.prefetch_profilepics(users))
    elapsed = time.time() - start

    sequential = delay * len(users)
    assert elapsed < sequential / 2, \
        f"took {elapsed:.2f}s, sequential would be {sequential:.2f}s - not running concurrently"


def test_prefetch_handles_an_empty_list():
    _, fake = with_cdn(lambda url: Response(404), lambda: miscellaneous.prefetch_profilepics([]))
    assert len(fake.timeouts) == 0, "an empty list should make no requests"


def test_prefetch_deduplicates_repeated_ids():
    _, fake = with_cdn(lambda url: Response(404),
                       lambda: miscellaneous.prefetch_profilepics(["u1", "u1", "u1"]))
    assert len(fake.timeouts) == 1, f"expected 1 lookup for a repeated id, got {len(fake.timeouts)}"


### ===============================================================================

if __name__ == "__main__":
    print("get_profilepic()")
    check("a timeout means no picture", test_a_timeout_means_no_picture)
    check("a timeout is passed to the request", test_a_timeout_is_actually_passed_to_the_request)
    check("missing picture returns None", test_missing_picture_returns_none)
    check("existing picture returns its url", test_existing_picture_returns_its_url)
    check("connection error still raises", test_connection_error_still_raises)

    print("\nprefetch_profilepics()")
    check("fills the cache for every user", test_prefetch_fills_the_cache_for_every_user)
    check("makes later lookups free", test_prefetch_makes_later_lookups_free)
    check("skips users already cached", test_prefetch_skips_users_already_cached)
    check("runs lookups concurrently", test_prefetch_runs_lookups_concurrently)
    check("handles an empty list", test_prefetch_handles_an_empty_list)
    check("deduplicates repeated ids", test_prefetch_deduplicates_repeated_ids)

    total, passed = len(PASSED), sum(PASSED)
    print(f"\n{passed}/{total} passed")
    sys.exit(0 if passed == total else 1)
