"""
module desc
"""

import requests
from kickbase.models.user import User
from kickbase.models.leagues import Leagues
from kickbase import exceptions

from pprint import pprint

def login(email: str, password: str):
    """
    Login to kickbase with the given credentials. Return "user" as dict and "leagues" as list of dicts.
    """
    url = "https://api.kickbase.com/user/login"
    headers = {
        "Content-Type": "application/json", # what we send
        "Accept": "application/json" # what we want to receive
    }
    payload = {
        "email": email,
        "password": password,
        "ext": False ### TODO: What is this?
    }

    ### Try to login with the given credentials via POST request
    try:
        json_response = requests.post(url, json=payload, headers=headers).json() # Save response as json
        pprint(json_response)
    except:
        raise exceptions.LoginException("Login failed! Please check your credentials.")

    ### Call the User class from models/user.py with json_response["user"] as parameter (dict)
    user = User(json_response["user"])
    ### iterating over the json_response["leagues"] list, where each entry is expected to be a dictionary. For each entry, it creates a new Leagues object.
    leagues = [Leagues(entry) for entry in json_response["leagues"]]
    ### Save the token
    token = json_response["token"]

    ### TODO: Set return type
    return user, leagues, token