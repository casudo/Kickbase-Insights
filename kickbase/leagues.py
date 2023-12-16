"""
### This module holds all necessary functions to call Kickbase `/leagues/...` API endpoints.

TODO: Maybe list all functions here automatically?
"""

import requests
from kickbase import exceptions

from kickbase.endpoints.leagues import League_User_Info, League_Feed, Market_Players


def league_user_info(token: str, league_id: str):
    """
    Get various information of the user in the given league.

    Expected response:
    ```json
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
    ```
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
    ### Collect the current gift.

    #### Expected response:  

    If not collected:
    ```json
        TODO: Add response
    ```

    If collected:
    ```json
        {"err":2080,"errMsg":"GiftAlreadyTaken"}
    ```
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
    ### Get the current players on the market in the league

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
    ### Get the statistics of a given player.

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

    #### Explanations:
    nm = next match
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


def league_users(token: str, league_id: str):
    """
    ### Get all users in the given league.

    Expected response:
    ```json
    {
        "users": [
            {
                "pt": 10261,
                "isu": false,
                "cbu": false,
                "id": "xxxx",
                "name": "COOLUSERNAME",
                "email": "coolmail@gmail.com",
                "status": 1,
                "profile": "https://kickbase.b-cdn.net/user/xxxx.jpeg",
                "cover": "https://kickbase.b-cdn.net/user/xxxx.jpeg",
                "flags": 1,
                "perms": [
                    1000
            },
            { ... },
        ]
    }
    ```
    Obviously, some user information have been redacted due to safety in the above response.
    """
    url = f"https://api.kickbase.com/leagues/{league_id}/users"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }
    # payload = { }

    ### Send GET request to get all users in the given league
    try:
        response = requests.get(url, headers=headers).json()
    except:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.") # TODO: Change exception
    
    return response


def user_players(token: str, league_id: str, user_id: str):
    """
    ### Get all players of a given user in the given league.

    Expected response:
    ```json
    {
        "items": [
            {
                "id": "0",
                "comments": 0,
                "date": "2023-11-25T10:16:16Z",
                "age": 7338,
                "type": 2,
                "source": 0,
                "meta": {
                    "sid": "2757595",
                    "pid": "2300",
                    "tid": "7",
                    "pfn": "Josip",
                    "pln": "Stanisic",
                    "p": 7328200.0
                },
                "seasonId": 0
            },
            { ... },
        ]
    }
    ```
    If the player was bought from a user, the following attributes are added to the "meta" dict:
    ```json
    meta: {
        "sid": "SELLERS_ID",
        "sn": "SELLERS_USERNAME",
        "si": "SELLERS_PROFILE_PIC"
    }
    ```
    If the player was sold to a user, the following attributes are added to the "meta" dict:
    ```json
    meta: {
        "bid": "BUYERS_ID",
        "bn": "BUYERS_USERNAME"
        "bi": "BUYERS_PROFILE_PIC"
    }
    ```
    """
    ### TODO: What does filter 12 do? 
    ### The feed always lists 25 entries, so we need to set start to 0 to get the first 25 entries. Then we can set start to 25 to get the next 25 entries and so on.
    start_point = 0
    query_params = f"?filter=12&start={start_point}"
    url = f"https://api.kickbase.com/leagues/{league_id}/users/{user_id}/feed{query_params}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }

    ### Send GET request to get the first 25 players of a given user in the given league
    try:
        response = requests.get(url, headers=headers).json()
    except:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.") # TODO: Change exception
    

    user_transfers = []
    ### As long as there are more than 25 entries, we need to send another GET request to get the next 25 entries.
    while response["items"]:
        user_transfers += response["items"]
        start_point += 25
        response = requests.get(f"https://api.kickbase.com/leagues/{league_id}/users/{user_id}/feed?filter=12&start={start_point}", headers=headers).json()

    return user_transfers


def user_stats(token: str, league_id: str, user_id: str):
    """
    Get the statistics of a given user in the given league.

    Expected response:
    ```json
    {
        "name": "xxx",
        "flags": 0,
        "profileUrl": "https://kickbase.b-cdn.net/user/xxxx.jpeg",
        "coverUrl": "https://kickbase.b-cdn.net/user/xxxx.jpeg",
        "placement": 6,
        "points": 7589,
        "teamValue": 287974376.0,
        "seasons": [
            {
                "seasonId": "20",
                "season": "2023/2024",
                "points": 7589,
                "averagePoints": 632,
                "maxPoints": 1045,
                "minPoints": 0,
                "wins": 1,
                "bought": 124,
                "sold": 109,
                "pointsGoalKeeper": 986,
                "pointsDefenders": 3331,
                "pointsMidFielders": 2452,
                "pointsForwards": 820,
                "averageGoalKeeper": 825,
                "averageDefenders": 2829,
                "averageMidFielders": 2622,
                "averageForwards": 1254
            },
            { evtl. mehrere Saisons },
        ],
        "teamValues": [
            {
                "d": "2023-11-28T23:00:00Z",
                "v": 273206442.0
            },
            {
                "d": "2023-11-27T23:00:00Z",
                "v": 264211798.0
            },
            { ... },
        ],
        "leagueUser": {
            "maxTeamValue": 287974376.0,
            "maxTeamValueDate": "2023-11-29T07:23:06Z",
            "maxBuyPrice": 35040052.0,
            "maxBuyPlayerId": "2383",
            "maxBuyFirstName": "Nico",
            "maxBuyLastName": "Schlotterbeck",
            "maxSellPrice": 22737700.0,
            "maxSellPlayerId": "163",
            "maxSellFirstName": "Niklas",
            "maxSellLastName": "Süle"
        }    
    }
    ```
    """
    url = f"https://api.kickbase.com/leagues/{league_id}/users/{user_id}/stats"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }

    ### Send GET request to get the statistics of a given user in the given league
    try:
        response = requests.get(url, headers=headers).json()
    except:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.") ### TODO: Change exception
    
    return response


def live_points(token: str, league_id: str):
    """
    ### Get the live points of all users in the given league.

    Expected response:
    ```json
    {
        "rtc": {
            "sk": "xxxx",
            "t": "rt",
            "st": "pubnub"
        },
        "lcn": "xxxx",
        "scn": "StatsV2C1",
        "epp": 1000.0,
        "md": [ ... ],   
        "u": [
            {
                "id": "xxxx",
                "n": "USERNAME",
                "i": "https://kickbase.b-cdn.net/user/xxxx.jpeg",
                "t": 419,
                "st": 12199,
                "b": 1.0,
                "pl": [
                    {
                        "id": "497",
                        "tid": "11",
                        "n": "Casteels",
                        "fn": "Koen",
                        "nr": 1,
                        "p": 1,
                        "t": 16,
                        "g": 0,
                        "r": 0,
                        "y": 0,
                        "yr": 0,
                        "a": 0,
                        "s": 1,
                        "mdst": 5
                    },
                    {
                        "id": "6668",
                        "tid": "2",
                        "n": "Kim",
                        "fn": "Min-Jae",
                        "nr": 3,
                        "p": 2,
                        "t": 42,
                        "g": 0,
                        "r": 0,
                        "y": 1,
                        "yr": 0,
                        "a": 0,
                        "s": 1,
                        "mdst": 5
                    },
                    { ..next player.. },
                ]
            },
            { ..next user.. },
        ]
    }
    ```
    """
    url = f"https://api.kickbase.com/leagues/{league_id}/live"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }

    ### Send GET request to get the live points of all users in the given league
    try:
        response = requests.get(url, headers=headers).json()
    except:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.") ### TODO: Change exception
    
    return response

### TODO: Unused?
def league_stats(token: str, league_id: str):
    """
    ### Get the league statistics.

    This includes the current match day, information about every previous match day and the users in the league.

    Expected response:
    ```json
    {
        "currentDay": 12,
        "matchDays": [
            {
                "day": 1,
                "users": [
                    {
                        "userId": "xxxx",
                        "dayPlacement": 0,
                        "dayTendency": 0,
                        "teamValue": 98354477.0,
                        "points": 0,
                        "placement": 1,
                        "tendency": 0,
                        "flags": 1
                    },
                    { the other users },
                ]
            },
            { the other days },
        ],
        "users": [
            {
                "id": "xxxx",
                "name": "xxxx",
                "email": "usermail",
                "status": 1,
                "profile": "https://kickbase.b-cdn.net/user/xxxx.jpeg",
                "cover": "https://kickbase.b-cdn.net/user/xxxx.jpeg",
                "flags": 1,
                "perms": []
            },
            { the other users },
        ]
    }
    ```
    """
    url = f"https://api.kickbase.com/leagues/{league_id}/stats"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }

    ### Send GET request to get the league statistics
    try:
        response = requests.get(url, headers=headers).json()
    except:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.") # TODO: Change exception
    
    return response