"""
### This module holds all necessary functions to call Kickbase `/competition/...` API endpoints.

TODO: Maybe list all functions here automatically?
"""

import requests

from backend import exceptions
from backend.kickbase.endpoints.competition import Player


def team_players(token: str, team_id: str):
    """
    ### Get all players of a given team
    
    Expected response:
    ```json
    {
        "p": [
            {
                "id": "237",
                "teamId": "2",
                "teamName": "Bayern",
                "teamSymbol": "FCB",
                "firstName": "Manuel",
                "lastName": "Neuer",
                "profile": "https://kickbase.b-cdn.net/pool/players/237.jpg",
                "profileBig": "https://kickbase.b-cdn.net/pool/playersbig/237.png",
                "team": "https://kickbase.b-cdn.net/team/2013/07/30/3ebe44c53c3f4c87bd605da69e743fb8.jpg",
                "teamCover": "https://kickbase.b-cdn.net/team/2013/08/01/ec8377d89197450e89fa942e4e36d48c.png",
                "status": 0,
                "position": 1,
                "number": 1,
                "averagePoints": 127,
                "totalPoints": 381,
                "marketValue": 19422256.0,
                "marketValueTrend": 1
            },
            { ... },
        ]
    }
    ```
    """
    url = f"https://api.kickbase.com/competition/teams/{team_id}/players"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }

    ### Send GET request to get all players of a given team
    try:
        response = requests.get(url, headers=headers).json()
    except:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.") # TODO: Change exception

    ### Create a new object for every entry in the response["p"] list.
    ### response["p"] holds all players of the given team.
    players_in_team = [Player(player) for player in response["p"]]

    return players_in_team