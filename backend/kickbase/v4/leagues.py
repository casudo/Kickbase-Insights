"""
### This module holds all necessary functions to call Kickbase `/leagues/...` API endpoints.

TODO: Maybe list all functions here automatically?
"""

import logging
import requests

from concurrent.futures import ThreadPoolExecutor

from backend import exceptions, miscellaneous
from backend.kickbase.endpoints.leagues import League_Info, Market_Players

### -------------------------------------------------------------------

### Per-run caches
## main.py walks every player twice, in market_value_changes() and in taken_free_players()
## and pages the activity feed three times. None of that changes during a run, so each response is fetched once and reused
MAX_PLAYER_WORKERS = 8

_player_statistics_cache = {}
_player_marketvalue_cache = {}
_transfers_cache = {}
_user_stats_cache = {}
_battles_cache = {}


def clear_caches() -> None:
    """### Empty the per-run API caches."""
    _player_statistics_cache.clear()
    _player_marketvalue_cache.clear()
    _transfers_cache.clear()
    _user_stats_cache.clear()
    _battles_cache.clear()

    #miscellaneous.clear_caches()


def get_league_list(token: str) -> list:
    """Get a list of all leagues the user is in.

    Args:
        user_token (str): The user token to authenticate the user.

    Returns:
        list: List of all leagues the user is in.
    """
    url = "https://api.kickbase.com/v4/leagues/selection"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }

    ### Send GET request
    try:
        json_response = requests.get(url, headers=headers).json()
    except:
        raise exceptions.KickbaseException("An exception was raised.") # TODO: Change
    
    ### Iterating over the json response, where each entry is expected to be a dictionary. For each entry, it creates a new Leagues_Info object.
    league_list = [League_Info(entry) for entry in json_response["it"]]

    return league_list


def get_market(token: str, league_id: str):
    """
    ### Get the current players on the market in the league

    Expected response:
    ```json
    {
        "it": [ ... ],
        "nps": 41,
        "tv": 69420,
        "mvud": "2023-11-24T21:00:00Z",
        "dt": "2023-11-24T19:30:00Z",
        "day": 12   
    }
    ```
    Obviously the "it" list is filled with all players on the market.
    """
    url = f"https://api.kickbase.com/v4/leagues/{league_id}/market"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }

    ### Send GET request to get all free players in the given league
    try:
        json_response = requests.get(url, headers=headers).json()
    except:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.") # TODO: Change exception
    
    ### Create a new object for every entry in the json_response["it"] list.
    players_on_market = [Market_Players(player) for player in json_response["it"]]

    return players_on_market


def prefetch_players(token: str, league_id: str, player_ids) -> None:
    """### Fetch statistics and market value history for many players at once.

    market_value_changes() needs both for every player (stats + market value) in the competition.
    They run concurrently and fill the same caches the individual functions use.

    Args:
        token (str): The user's kkstrauth token.
        league_id (str): The league to fetch statistics for.
        player_ids (iterable): The player IDs to fetch.
    """
    ids = sorted({str(player_id) for player_id in player_ids})

    missing_statistics = [p for p in ids if (league_id, p) not in _player_statistics_cache]
    missing_marketvalues = [p for p in ids if p not in _player_marketvalue_cache]

    if not missing_statistics and not missing_marketvalues:
        return

    logging.debug(f"Prefetching {len(missing_statistics)} player statistic(s) "
                  f"and {len(missing_marketvalues)} market value history/histories...")

    with ThreadPoolExecutor(max_workers=MAX_PLAYER_WORKERS) as executor:
        futures = [executor.submit(player_statistics, token, league_id, p)
                   for p in missing_statistics]
        futures += [executor.submit(player_marketvalue, token, p)
                    for p in missing_marketvalues]

        ### Surface any exception rather than letting it disappear into the pool
        for future in futures:
            future.result()


def player_statistics(token: str, league_id: str, player_id: str):
    """
    ### Get the statistics of a given player.
    """
    cache_key = (league_id, str(player_id))
    if cache_key in _player_statistics_cache:
        return _player_statistics_cache[cache_key]

    url = f"https://api.kickbase.com/v4/competitions/1/players/{player_id}?leagueId={league_id}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Language": "de-DE,de;q=0.9", # localized for 'stxt' (status)
        "Cookie": f"kkstrauth={token};",
    }

    ### Send GET request to get the market value changes of ALL players in the league
    try:
        json_response = requests.get(url, headers=headers).json()
    except:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.") # TODO: Change exception

    _player_statistics_cache[cache_key] = json_response

    return json_response


def player_marketvalue(token: str, player_id: str):
    """
    ### Get the market value history of a given player.
    """
    cache_key = str(player_id)
    if cache_key in _player_marketvalue_cache:
        return _player_marketvalue_cache[cache_key]

    url_1year = f"https://api.kickbase.com/v4/competitions/1/players/{player_id}/marketValue/365"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }

    ### Send GET request to get the market value changes of ALL players in the league
    try:
        json_response = requests.get(url_1year, headers=headers).json()
    except:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.") # TODO: Change exception

    _player_marketvalue_cache[cache_key] = json_response["it"]

    return json_response["it"] ### Only return the "it" list


def get_users(token: str, league_id: str):
    """
    ### Get all users and their IDs in the lague.
    """
    url = f"https://api.kickbase.com/v4/leagues/{league_id}/overview?includeManagersAndBattles=true"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }

    ### Send GET request to get the market value changes of ALL players in the league
    try:
        json_response = requests.get(url, headers=headers).json()
    except:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.") # TODO: Change exception
    
    ### Create a dictionary to map user IDs to user names
    user_id_to_name = {user["i"]: user["n"] for user in json_response["us"]}
    miscellaneous.write_json_to_file(user_id_to_name, "STATIC_users.json")
    
    return json_response["us"] ### Only return the "us" list which contains alls usernames and IDs


def transfers(token: str, league_id: str) -> dict:
    """### Get all transfers of all users in a league.

    Args:
        token (str): The user's kkstrauth token.
        league_id (str): The league ID.

    Returns:
        dict: A dictionary containing the user's players.
    """
    if league_id in _transfers_cache:
        return _transfers_cache[league_id]

    start_point = 0
    user_transfers = []

    while True:
        query_params = f"?max=26&start={start_point}"
        url = f"https://api.kickbase.com/v4/leagues/{league_id}/activitiesFeed/{query_params}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Cookie": f"kkstrauth={token};",
        }

        ### Send GET request to get the next 26 entries
        try:
            json_response = requests.get(url, headers=headers).json()
        except Exception as e:
            raise exceptions.NotificatonException(f"Notification failed! Please check your Discord Webhook URL. Error: {e}") # TODO: Change exception

        ### Filter transfers where "t" == 15
        filtered_transfers = [entry for entry in json_response.get("af", []) if entry.get("t") == 15]
        user_transfers += filtered_transfers

        ### Check if there are more entries to fetch
        if not json_response.get("af"):
            break

        start_point += 26

    _transfers_cache[league_id] = user_transfers

    return user_transfers


def user_stats(token: str, league_id: str, user_id: str) -> dict:
    """
    Get the statistics of a given user in the given league.
    """
    cache_key = (league_id, str(user_id))
    if cache_key in _user_stats_cache:
        return _user_stats_cache[cache_key]

    url = f"https://api.kickbase.com/v4/leagues/{league_id}/managers/{user_id}/dashboard"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }

    ### Send GET request to get the statistics of a given user in the given league
    try:
        json_response = requests.get(url, headers=headers).json()
    except:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.") ### TODO: Change exception

    _user_stats_cache[cache_key] = json_response

    return json_response


def user_performance(token: str, league_id: str, user_id: str) -> dict:
    """
    Get the performance of a given user in the given league.
    """
    url = f"https://api.kickbase.com/v4/leagues/{league_id}/managers/{user_id}/performance"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }

    ### Send GET request to get the statistics of a given user in the given league
    try:
        json_response = requests.get(url, headers=headers).json()
    except:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.") ### TODO: Change exception
    
    return json_response


def ranking(token: str, league_id: str, match_day: int) -> dict:
    """
    ### Get the ranking of the league.
    """
    query_params = f"?dayNumber={match_day}"
    url = f"https://api.kickbase.com/v4/leagues/{league_id}/ranking/{query_params}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }

    ### Send GET request to get the ranking of the league
    try:
        json_response = requests.get(url, headers=headers).json()
    except:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.") ### TODO: Change exception
    
    return json_response


def live_points(token: str, league_id: str) -> dict:
    """
    ### Get the live points of all users in the given league.

    Expected response:
    ```json
    {
        "u": [
            {
                "id": "xxxx",       ### User ID
                "n": "USERNAME",
                "t": 419,           ### Live points
                "st": 12199,        ### Total points
                "pl": [ ... ]       ### Players of the user
            }
        ]
    }
    ```

    NOTE: This still targets the legacy (v1) `/leagues/{id}/live` endpoint, since
    Kickbase has no v4 equivalent implemented here yet. The live points feature is
    on-hold, so this call is unverified against the current API.
    """
    url = f"https://api.kickbase.com/leagues/{league_id}/live"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }

    ### Send GET request to get the live points of the league
    try:
        json_response = requests.get(url, headers=headers).json()
    except:
        raise exceptions.KickbaseException("Couldn't get the live points of the league.")

    return json_response


def battles(token: str, league_id: str, battle_id: int) -> dict:
    """
    ### Get the battles of the league.
    """
    cache_key = (league_id, battle_id)
    if cache_key in _battles_cache:
        return _battles_cache[cache_key]

    url = f"https://api.kickbase.com/v4/leagues/{league_id}/battles/{battle_id}/users"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }

    ### Send GET request to get the battles of the league
    try:
        json_response = requests.get(url, headers=headers).json()
    except:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.") ### TODO: Change exception

    _battles_cache[cache_key] = json_response

    return json_response