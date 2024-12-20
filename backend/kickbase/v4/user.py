"""
### This module holds all necessary functions to call Kickbase `/user/...` API endpoints.

TODO: Maybe list all functions here automatically?
"""

import requests

from backend import exceptions, miscellaneous
from backend.kickbase.endpoints.user import User

### -------------------------------------------------------------------


def login(email: str, password: str, discord_webhook: str) -> tuple:
    """### Logs in the user with the provided email and password.

    Args:
        email (str): The email of the user.
        password (str): The password of the user.
        discord_webhook (str): The Discord webhook URL to send a notification in case of an error.

    Raises:
        exceptions.LoginException: Raised if the login fails.

    Returns:
        tuple: A tuple containing the user info and token.
    """
    url = "https://api.kickbase.com/v4/user/login"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "em": email,
        "pass": password,
        "ext": True, # TODO: What is this?
        "loy": False, # TODO: What is this?
        "rep": {} # TODO: What is this?
    }

    ### Try to login with the given credentials via POST request
    try:
        json_response = requests.post(url, json=payload, headers=headers).json() # Save response as json
    except:
        miscellaneous.discord_notification("Login failed!", "Please check your credentials.", 16711680, discord_webhook)
        raise exceptions.LoginException("[CRITICAL] Login failed! Please check your credentials.")
    
    ### Create an object "user" with the User class with json_response["u"] as parameter (dict)
    user = User(json_response["u"])
    ### Save the token
    token = json_response["tkn"]

    ### TODO: Set return type
    return user, token


def collect_gift(token: str) -> dict:
    """### Collects the current gift of the user in every league.

    Args:
        token (str): The token of the user.

    Returns:
        dict: The response of the API call.
    """
    url = "https://api.kickbase.com/v4/bonus/collect"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }

    ### Send GET request to get the current gift
    try:
        json_response = requests.get(url, headers=headers).json()
    except:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.") # TODO: Change exception
    
    return json_response