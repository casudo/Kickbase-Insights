"""
### This module holds all necessary functions to call Kickbase `/leagues/...` API endpoints.

TODO: Maybe list all functions here automatically?
"""

import requests
from kickbase import exceptions

from kickbase.endpoints.leagues import League_User_Info, League_Feed, Market_Players

import json


def league_user_info(token: str, league_id: str):
    """
    Get various information of the user in the given league.

    Expected response:
    {
        "budget":-47379036.0,
        "teamValue":251533368.0,
        "placement":7,
        "points":6683,
        "ttm":809244,
        "cmd":12,
        "flags":0,
        "perms":[],
        "se":false,
        "csid":20,
        "nt":false,
        "ntv":100000000.0,
        "nb":50000000.0,
        "ga":false,
        "un":0
    }
    """
    url = f"https://api.kickbase.com/leagues/{league_id}/me"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }

    ### Send GET request to get information about the user in the given league
    try:
        json_response = requests.get(url, headers=headers).json()
    except:
        raise exceptions.KickbaseException("An exception was raised.") # TODO: Change
    
    league_user_info = League_User_Info(json_response)

    return league_user_info


def league_feed(token: str, league_id: str):
    """
    Get the league feed. (no events as far as I can tell)
    """
    url = f"https://api.kickbase.com/leagues/{league_id}/feed?start=0"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }

    ### Send GET request to get the league feed
    try:
        response = requests.get(url, headers=headers).json()
    except:
        raise exceptions.KickbaseException("An exception was raised.") # TODO: Change
    
    ### Create a new object for every entry in the response["items"] list.
    ### response["items"] holds all entries of the league feed.
    feed = [League_Feed(feed_entry) for feed_entry in response["items"]]

    return feed


def is_gift_available(token: str, league_id: str):
    """
    Check if a gift is available.
    
    Expected response:
    {   
        'isAvailable': Bool, 
        'amount': Double,
        'level': Int,
        'il': Bool,
        'is': Bool,
    }
    """
    url = f"https://api.kickbase.com/leagues/{league_id}/currentgift"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }
    # payload = { }

    ### Send GET request to get information about the current gift
    try:
        response = requests.get(url, headers=headers).json()
    except:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.") # TODO: Change exception
    
    return response


def get_gift(token: str, league_id: str):
    """
    Get the current gift.

    Expected response:
    IF NOT COLLECTED:
    TODO: Add response
    
    IF COLLECTED:
    {"err":2080,"errMsg":"GiftAlreadyTaken"}
    """
    url = f"https://api.kickbase.com/leagues/{league_id}/collectgift"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }
    # payload = { }

    ### Send POST request to get the current gift
    try:
        response = requests.post(url, headers=headers).json()
    except:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.") # TODO: Change exception
    
    return response


def get_market(token: str, league_id: str):
    """
    Get the current players on the market in the league

    Expected response:
    ```json
    {
        "c": false,
        "players": [ ... ],
        "mvud": "2023-11-24T21:00:00Z",
        "dt": "2023-11-24T19:30:00Z",
        "day": 12   
    }
    Obviously the "players" list is filled with all players on the market.
    ```
    """
    url = f"https://api.kickbase.com/leagues/{league_id}/market"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }
    # payload = { }

    ### Send GET request to get all free players in the given league
    try:
        response = requests.get(url, headers=headers).json()
    except:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.") # TODO: Change exception
    
    ### Create a new object for every entry in the response["players"] list.
    players_on_market = [Market_Players(player) for player in response["players"]]

    ### TODO: In case we want to use the whole response, we can do it here.
    ### Paste the whole response into market_whole.json
    # with open("market_whole.json", "w") as f:
    #     f.write(json.dumps(response, indent=2))

    return players_on_market


def player_statistics(token: str, league_id: str, player_id: str):
    """
    Get the statistics of a given player.

    Expected response:
    ```json
    {
        "mvHigh": 22898922.0,
        "mvHighDate": "2022-12-09T00:00:00Z",
        "mvLow": 500000.0,
        "mvLowDate": "2023-04-07T00:00:00Z",
        "marketValues": [ 
            {
                "d": "2022-11-23T00:00:00Z",
                "m": 22415981.0
            },
            {
                "d": "2022-11-24T00:00:00Z",
                "m": 22496548.0
            },
            { ... },
        ],
        "f": false,
        "id": "237",
        "teamId": "2",
        "userFlags": 0,
        "firstName": "Manuel",
        "lastName": "Neuer",
        "profileUrl": "https://kickbase.b-cdn.net/pool/players/237.jpg",
        "teamUrl": "https://kickbase.b-cdn.net/team/2013/07/30/3ebe44c53c3f4c87bd605da69e743fb8.jpg",
        "teamCoverUrl": "https://kickbase.b-cdn.net/team/2013/08/01/ec8377d89197450e89fa942e4e36d48c.png",
        "status": 0,
        "position": 1,
        "number": 1,
        "points": 381,
        "averagePoints": 127,
        "marketValue": 19422256.0,
        "mvTrend": 1,
        "seasons": [ ... ],
        "nm": [ ... ],
        "sl": true,
    }
    ```
    The given attributes may change if the player is owned by a user!
    """
    url = f"https://api.kickbase.com/leagues/{league_id}/players/{player_id}/stats"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }
    # payload = { }

    ### Send GET request to get the market value changes of ALL players in the league
    try:
        response = requests.get(url, headers=headers).json()
    except:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.") # TODO: Change exception
    
    return response