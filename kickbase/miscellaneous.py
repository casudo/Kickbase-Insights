"""
### This module holds all functions that are not related to Kickbase API in any point.

TODO: Maybe list all functions here automatically?
"""

import requests
from kickbase import exceptions


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