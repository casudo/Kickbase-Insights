"""
### This module holds all functions and constants that are not related to Kickbase API in any point.

TODO: Maybe list all functions here automatically?
"""

import requests
from kickbase import exceptions

### ===============================================================================

POSITIONS = {1: 'TW', 2: 'ABW', 3: 'MF', 4: 'ANG'}
### TREND?
### STATUS
### TYPE

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