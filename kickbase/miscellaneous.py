"""
module desc
"""

import requests
from kickbase import exceptions

def discord_notification(title: str, message: str, color: int):
    """
    Send a notification to a Discord Webhook.
    """
    url = "YOUR_URL"
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
    

### TODO: WIP
def post_chat_message(self, message: str, league_id: str):
    """
    Post a message to the chat of the given league.
    """
    url = f"https://firestore.googleapis.com/v1/projects/kickbase-bdb0f/databases/(default)/documents/chat/{league_id}/messages"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": self.auth_token
    }
    payload = {
        "message": message,
        "leagueId": league_id
    }

    ### Send POST request to chat
    try:
        response = requests.post(url, json=payload, headers=headers)
    except:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.")
        

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