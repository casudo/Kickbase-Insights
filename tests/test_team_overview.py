"""Tests for the team overview probe.

There is no endpoint listing the teams in a competition, so team ids are probed
one by one. The competition has 18 teams and the probe covers ids 2 to 100, so
most requests find nothing. Done sequentially that was 10 seconds of every run.

    ./venv/bin/python tests/test_team_overview.py
"""

import sys
import tempfile

from os import path

sys.path.insert(0, path.dirname(path.dirname(path.abspath(__file__))))

import requests as real_requests

from backend import miscellaneous
from backend.kickbase.v4 import competitions

### ===============================================================================

PASSED = []


def check(name, fn):
    ### Writes go to a temporary directory, never the real data directory
    with tempfile.TemporaryDirectory() as tmp:
        original = (miscellaneous.DATA_DIR, miscellaneous.TIMESTAMP_DIR)
        miscellaneous.DATA_DIR = tmp
        miscellaneous.TIMESTAMP_DIR = path.join(tmp, "timestamps")
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
        finally:
            miscellaneous.DATA_DIR, miscellaneous.TIMESTAMP_DIR = original


### Team ids that "exist" in the fake competition
REAL_TEAMS = {2: "Bayern", 3: "Dortmund", 7: "Leverkusen", 40: "Union"}


class FakeResponse:
    def __init__(self, payload, content=b"x"):
        self._payload = payload
        self.content = content

    def json(self):
        return self._payload

    def raise_for_status(self):
        pass


class MissingTeam(FakeResponse):
    def raise_for_status(self):
        raise real_requests.exceptions.HTTPError("404")


class FakeApi:
    exceptions = real_requests.exceptions

    def __init__(self, delay=0):
        self.urls = []
        self.delay = delay

    def get(self, url, headers=None, timeout=None):
        import time

        self.urls.append(url)
        if self.delay:
            time.sleep(self.delay)

        team_id = int(url.rstrip("/").split("/teams/")[1].split("/")[0])
        if team_id in REAL_TEAMS:
            return FakeResponse({
                "tid": str(team_id),
                "tn": REAL_TEAMS[team_id],
                "it": [{"i": f"p{team_id}", "n": "Player"}],
            })
        return MissingTeam({})


def with_api(api, fn):
    original = competitions.requests
    competitions.requests = api
    try:
        return fn()
    finally:
        competitions.requests = original


### ===============================================================================


def test_finds_every_existing_team():
    api = FakeApi()
    teams = with_api(api, lambda: competitions.get_team_overview("token"))

    found = {t["teamName"] for t in teams}
    assert found == set(REAL_TEAMS.values()), f"expected {set(REAL_TEAMS.values())}, got {found}"


def test_keeps_teams_in_id_order():
    """STATIC_teams.json should not reshuffle between runs."""
    api = FakeApi()
    teams = with_api(api, lambda: competitions.get_team_overview("token"))

    ids = [int(t["teamId"]) for t in teams]
    assert ids == sorted(ids), f"teams came back out of order: {ids}"


def test_still_skips_the_broken_team_ids():
    """33 and 38 return 500s and were skipped before."""
    api = FakeApi()
    with_api(api, lambda: competitions.get_team_overview("token"))

    probed = {int(u.rstrip("/").split("/teams/")[1].split("/")[0]) for u in api.urls}
    assert 33 not in probed, "team id 33 should be skipped"
    assert 38 not in probed, "team id 38 should be skipped"


def test_probes_concurrently():
    """99 probes to find 18 teams must not run one after another."""
    import time

    delay = 0.01
    api = FakeApi(delay=delay)

    start = time.time()
    with_api(api, lambda: competitions.get_team_overview("token"))
    elapsed = time.time() - start

    sequential = delay * len(api.urls)
    assert elapsed < sequential / 3, \
        f"took {elapsed:.2f}s, sequential would be {sequential:.2f}s - not concurrent"


### ===============================================================================

if __name__ == "__main__":
    print("get_team_overview()")
    check("finds every existing team", test_finds_every_existing_team)
    check("keeps teams in id order", test_keeps_teams_in_id_order)
    check("still skips the broken team ids", test_still_skips_the_broken_team_ids)
    check("probes concurrently", test_probes_concurrently)

    total, passed = len(PASSED), sum(PASSED)
    print(f"\n{passed}/{total} passed")
    sys.exit(0 if passed == total else 1)
