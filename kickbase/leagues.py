"""
### This module holds all necessary functions to call Kickbase `/leagues/...` API endpoints.

TODO: Maybe list all functions here automatically?
"""

import requests
from kickbase import exceptions

from kickbase.endpoints.leagues import League_User_Info, League_Feed


def league_user_info(token: str, league_id: str):
    """
    Get various information of the user in the given league.

    Expected response:
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
    Get the current gift.

    Expected response:
    IF NOT COLLECTED:
    TODO: Add response
    
    IF COLLECTED:
    {"err":2080,"errMsg":"GiftAlreadyTaken"}
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