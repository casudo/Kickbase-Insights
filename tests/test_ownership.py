"""Tests for reading player ownership out of a player_statistics response.

Kickbase moved ownership from the top level "oui" field into the per-league "opl"
list. The top level field still exists but is always "0", so the old check
classified every player as free.

Shapes below are taken from real API responses.

    ./venv/bin/python tests/test_ownership.py
"""

import sys

from os import path

sys.path.insert(0, path.dirname(path.dirname(path.abspath(__file__))))

from backend import miscellaneous

### ===============================================================================

LEAGUE_ID = "11412166"
OTHER_LEAGUE_ID = "99999999"

PASSED = []


def check(name, fn):
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


### Paul Okon-Engstler, owned by Meier. Note the top level "oui" is "0".
OWNED_PLAYER = {
    "i": "14300",
    "fn": "Paul",
    "ln": "Okon-Engstler",
    "oui": "0",
    "opl": [{
        "li": LEAGUE_ID,
        "oui": "2592773",
        "lnm": "Kickbase-Elite 26/27",
        "onm": "Meier",
        "iposl": False,
    }],
}

### A player nobody in this league owns
FREE_PLAYER_EMPTY_LIST = {"i": "173", "fn": "Jonathan", "ln": "Tah", "oui": "0", "opl": []}

### The same, but the API omits the list entirely
FREE_PLAYER_NO_LIST = {"i": "173", "fn": "Jonathan", "ln": "Tah", "oui": "0"}


def test_finds_the_owner_id_for_the_league():
    owner = miscellaneous.get_player_owner(OWNED_PLAYER, LEAGUE_ID)
    assert owner is not None, "expected an owner, got None"
    assert owner["oui"] == "2592773", f"expected owner id 2592773, got {owner}"


def test_exposes_the_owner_name():
    owner = miscellaneous.get_player_owner(OWNED_PLAYER, LEAGUE_ID)
    assert owner["onm"] == "Meier", f"expected owner name Meier, got {owner}"


def test_free_player_with_empty_list_has_no_owner():
    assert miscellaneous.get_player_owner(FREE_PLAYER_EMPTY_LIST, LEAGUE_ID) is None


def test_free_player_without_the_list_has_no_owner():
    assert miscellaneous.get_player_owner(FREE_PLAYER_NO_LIST, LEAGUE_ID) is None


def test_ownership_in_a_different_league_does_not_count():
    """A player owned in another league of the same user is free in this one."""
    player = {
        "i": "500",
        "oui": "0",
        "opl": [{"li": OTHER_LEAGUE_ID, "oui": "123", "onm": "SomeoneElse"}],
    }
    assert miscellaneous.get_player_owner(player, LEAGUE_ID) is None


def test_picks_the_right_league_when_several_are_present():
    player = {
        "i": "500",
        "oui": "0",
        "opl": [
            {"li": OTHER_LEAGUE_ID, "oui": "123", "onm": "SomeoneElse"},
            {"li": LEAGUE_ID, "oui": "2592773", "onm": "Meier"},
        ],
    }
    owner = miscellaneous.get_player_owner(player, LEAGUE_ID)
    assert owner["onm"] == "Meier", f"expected Meier, got {owner}"


def test_legacy_top_level_oui_is_ignored():
    """The old field must not be trusted, even if it were somehow set."""
    player = {"i": "500", "oui": "2592773", "opl": []}
    assert miscellaneous.get_player_owner(player, LEAGUE_ID) is None, \
        "the vestigial top level oui must not be treated as ownership"


### ===============================================================================
### taken_free_players() end to end
### ===============================================================================


def test_owned_player_lands_in_taken_not_free():
    """The reported bug: an owned player was written to free_players.json."""
    import json
    import tempfile
    from os import environ, makedirs

    import main
    from backend.kickbase.v4 import leagues

    with tempfile.TemporaryDirectory() as tmp:
        data_dir = path.join(tmp, "data")
        ts_dir = path.join(data_dir, "timestamps")
        makedirs(ts_dir, exist_ok=True)

        with open(path.join(data_dir, "STATIC_users.json"), "w") as f:
            json.dump({"2592773": "Meier", "111": "shirazzi"}, f)

        ### Two players on one team: one owned by Meier, one owned by nobody
        with open(path.join(data_dir, "STATIC_teams.json"), "w") as f:
            json.dump([{
                "teamId": "28",
                "teamName": "Koeln",
                "players": [
                    {"i": "14300", "n": "Okon-Engstler", "pos": 3, "mv": 3062573, "st": 0, "mvt": 1, "tid": "28"},
                    {"i": "173", "n": "Tah", "pos": 2, "mv": 36549128, "st": 0, "mvt": 1, "tid": "2"},
                ],
            }], f)

        stats_by_id = {"14300": OWNED_PLAYER, "173": FREE_PLAYER_EMPTY_LIST}

        original = (main.DATA_DIR, miscellaneous.DATA_DIR, miscellaneous.TIMESTAMP_DIR,
                    leagues.transfers, leagues.player_statistics, leagues.player_marketvalue)
        main.DATA_DIR = data_dir
        miscellaneous.DATA_DIR = data_dir
        miscellaneous.TIMESTAMP_DIR = ts_dir

        try:
            environ["START_DATE"] = "2026-08-01T18:00:00Z"
            leagues.transfers = lambda token, lid: []
            leagues.player_statistics = lambda token, lid, pid: stats_by_id[str(pid)]
            leagues.player_marketvalue = lambda token, pid: []

            class FakeLeague:
                id = LEAGUE_ID
                name = "Kickbase-Elite 26/27"

            main.taken_free_players("token", FakeLeague())

            with open(path.join(data_dir, "taken_players.json")) as f:
                taken = json.load(f)
            with open(path.join(data_dir, "free_players.json")) as f:
                free = json.load(f)
        finally:
            (main.DATA_DIR, miscellaneous.DATA_DIR, miscellaneous.TIMESTAMP_DIR,
             leagues.transfers, leagues.player_statistics,
             leagues.player_marketvalue) = original

    taken_ids = [p["playerId"] for p in taken]
    free_ids = [p["playerId"] for p in free]

    assert "14300" in taken_ids, f"the owned player must be taken, got taken={taken_ids} free={free_ids}"
    assert "14300" not in free_ids, "the owned player must not also be free"
    assert "173" in free_ids, f"the unowned player must be free, got free={free_ids}"
    assert taken[0]["owner"] == "Meier", f"expected owner Meier, got {taken[0]['owner']}"


### ===============================================================================

if __name__ == "__main__":
    print("get_player_owner()")
    check("finds the owner id for the league", test_finds_the_owner_id_for_the_league)
    check("exposes the owner name", test_exposes_the_owner_name)
    check("free player with empty list has no owner", test_free_player_with_empty_list_has_no_owner)
    check("free player without the list has no owner", test_free_player_without_the_list_has_no_owner)
    check("ownership in another league does not count", test_ownership_in_a_different_league_does_not_count)
    check("picks the right league among several", test_picks_the_right_league_when_several_are_present)
    check("ignores the legacy top level oui", test_legacy_top_level_oui_is_ignored)

    print("\ntaken_free_players()")
    check("owned player lands in taken, not free", test_owned_player_lands_in_taken_not_free)

    total, passed = len(PASSED), sum(PASSED)
    print(f"\n{passed}/{total} passed")
    sys.exit(0 if passed == total else 1)
