"""
### This module holds all functions and constants that are not related to Kickbase API in any point.

TODO: Maybe list all functions here automatically?
"""

import requests
from kickbase import exceptions, competition
import json

### ===============================================================================

POSITIONS = {1: 'TW', 2: 'ABW', 3: 'MF', 4: 'ANG'}
### TREND?
### STATUS

### TYPE
# Type 2: Verkauft an Kickbase
# Type 2 + meta[bn]: Verkauft an Spieler (bn = buyerName)
# Type 12: Gekauft von Kickbase
# Type 12 + meta[sn]: Gekauft von Spieler (sn = sellerName)



### TEAM_IDS
### TODO: Update with missing teams
# 2 Bayern
# 3 BVB
# 4 Frankfurt
# 5 Freiburg
# 7 Bayer
# 8 Schalke
# 9 Stuttgart
# 10 Bremen
# 11 Wolfsburg
# 13 Augsburg
# 14 Hoffenheim
# 15 Gladbach
# 18 Mainz
# 20 Hertha
# 24 Bochum
# 28 Köln
# 40 Union
# 42 Darmstadt
# 43 Leipzig
# 50 Heidenheim
TEAM_IDS = [2, 3, 4, 5, 7, 9, 10, 11, 13, 14, 15, 18, 24, 28, 40, 42, 43, 50]

### ===============================================================================

def discord_notification(title: str, message: str, color: int):
    """
    Send a notification to a Discord Webhook.
    """
    url = "url"
    headers = {"Content-Type": "application/json"}
    payload = {
        "username": "Kickbase",
        "avatar_url": "https://upload.wikimedia.org/wikipedia/commons/2/2c/Kickbase_Logo.jpg",
        "embeds": [
            {
                "title": title,
                "description": message,
                "color": color
            }
        ]
    }

    ### Send POST request to Webhook
    try:
        requests.post(url, json=payload, headers=headers)
    except:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.")
    

def get_free_players(token: str, league_id: str, taken_players):
    """
    TODO: Add docstring
    """
    free_players = []

    ### Get all taken player ids
    taken_player_ids = [player["playerId"] for player in taken_players]

    ### Cycle through all teams and get the players who are not taken
    for team_id in TEAM_IDS:
        ### Cycle through all players of the team
        for player in competition.team_players(token, team_id):
            ### Check if the player is not taken
            if player.p.id not in taken_player_ids:

                free_players.append({
                    "playerId": player.p.id,
                    "teamId": player.p.teamId,
                    "position": POSITIONS[player.p.position],
                    "firstName": player.p.firstName,
                    "lastName": player.p.lastName,
                    "marketValue": player.p.marketValue,
                    "trend": player.p.marketValueTrend,
                    "points": player.p.totalPoints,
                })

    with open("frontend/data/free_players.json", "w") as file:
        file.write(json.dumps(free_players, indent=2))
