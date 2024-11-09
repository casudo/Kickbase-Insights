"""
### This module holds all necessary functions to call Kickbase `/competition/...` API endpoints.

TODO: Maybe list all functions here automatically?
"""

import requests

from backend import exceptions
from backend.kickbase.endpoints.competition import Player


def team_players(token: str, team_id: str):
    """
    ### Get all players of a given team.
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