"""
### This module holds all necessary functions to call Kickbase `/user/...` API endpoints.

TODO: Maybe list all functions here automatically?
"""

import requests

from backend import exceptions
from backend.kickbase.endpoints.user import User, League

### -------------------------------------------------------------------


def login(email: str, password: str) -> tuple:
    """Logs in the user with the provided email and password.

    Args:
        email (str): The email of the user.
        password (str): The password of the user.

    Raises:
        exceptions.LoginException: Raised if the login fails.

    Returns:
        tuple: A tuple containing the user dict, leagues list, and token.
    """
    url = "https://api.kickbase.com/user/login"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "email": email,
        "password": password,
        "ext": False ### TODO: What is this?
    }

    ### Try to login with the given credentials via POST request
    try:
        json_response = requests.post(url, json=payload, headers=headers).json() # Save response as json
    except:
        raise exceptions.LoginException("[CRITICAL] Login failed! Please check your credentials.")

    ### Call the User class from models/user.py with json_response["user"] as parameter (dict)
    user = User(json_response["user"])
    ### Iterating over the json_response["leagues"] list, where each entry is expected to be a dictionary. For each entry, it creates a new Leagues object.
    leagues = [League(entry) for entry in json_response["leagues"]]
    ### Save the token
    token = json_response["token"]

    ### TODO: Set return type
    return user, leagues, token