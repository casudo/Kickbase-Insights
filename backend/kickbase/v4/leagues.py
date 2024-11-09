"""
### This module holds all necessary functions to call Kickbase `/leagues/...` API endpoints.

TODO: Maybe list all functions here automatically?
"""

import requests

from backend import exceptions
from backend.kickbase.endpoints.leagues import League_Info, Market_Players


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


def player_statistics(token: str, league_id: str, player_id: str):
    """
    ### Get the statistics of a given player.
    """
    url = f"https://api.kickbase.com/v4/competitions/1/players/{player_id}?leagueId={league_id}"
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
    
    return json_response


def player_marketvalue(token: str, league_id: str, player_id: str):
    """
    ### Get the statistics of a given player.
    """
    url = f"https://api.kickbase.com/v4/competitions/1/players/{player_id}/marketValue/92?leagueId={league_id}"
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
    
    return json_response["us"] ### Only return the "us" list which contains alls usernames and IDs