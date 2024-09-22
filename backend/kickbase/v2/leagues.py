"""
### This module holds all necessary functions to call Kickbase `/v2/leagues/...` API endpoints.
"""

import requests

from backend import exceptions


def transfers(token: str, league_id: str) -> dict:
    """### Get all transfers of all user in a league.
    
    NOTE: The response only contains the last 330 transfers!! Until `&start=300`.

    Args:
        token (str): The user's kkstrauth token.
        league_id (str): The league ID.

    Returns:
        dict: A dictionary containing the user's players.

    #### Expected response:
    ```json
    {
        "items": [
            {
                "id": "xxxxx",
                "comments": 0,
                "date": "2024-07-30T11:42:11Z",
                "age": 3428,
                "type": 15,
                "source": 2,
                "meta": {
                    "s": {
                        "i": "xx",
                        "n": "xx",
                        "f": "https://kickbase.b-cdn.net/user/xx.jpeg"
                    },
                    "b": {
                        "i": "xx",
                        "n": "xx",
                        "f": "https://kickbase.b-cdn.net/user/xx.png"
                    },
                    "p": {
                        "i": "493",
                        "t": "5",
                        "n": "Gregoritsch",
                        "f": "https://kickbase.b-cdn.net/pool/players/493.jpg",
                        "s": 38,
                        "p": 4
                    },
                    "v": 12000000.0,
                    "st": {
                        "e": {
                            "team": {
                                "color": 13703706
                            },
                            "text": {
                                "color": 4294967295
                            }
                        }
                    }
                },
                "seasonId": 0
            },
            {
                "id": "xxxxx",
                "comments": 0,
                "date": "2024-07-30T11:41:11Z",
                "age": 3488,
                "type": 15,
                "source": 2,
                "meta": {
                    "b": {
                        "i": "xx",
                        "n": "xx",
                        "f": "https://kickbase.b-cdn.net/user/xx.jpeg"
                    },
                    "p": {
                        "i": "1862",
                        "t": "2",
                        "n": "Guerreiro",
                        "f": "https://kickbase.b-cdn.net/pool/players/1862.jpg",
                        "s": 22,
                        "p": 2
                    },
                    "v": 14100000.0,
                    "st": {
                        "e": {
                            "team": {
                                "color": 14419245
                            },
                            "text": {
                                "color": 4294967295
                            }
                        }
                    }
                },
                "seasonId": 0
            },
            {
                "id": "xxxxx",
                "comments": 0,
                "date": "2024-07-30T06:47:56Z",
                "age": 21083,
                "type": 15,
                "source": 2,
                "meta": {
                    "s": {
                        "i": "xx",
                        "n": "xx",
                        "f": "https://kickbase.b-cdn.net/user/xx.jpeg"
                    },
                    "p": {
                        "i": "3102",
                        "t": "3",
                        "n": "Rothe",
                        "s": 0,
                        "p": 2
                    },
                    "v": 7536938.0,
                    "st": {
                        "e": {
                            "team": {
                                "color": 16638208
                            },
                            "text": {
                                "color": 4294967295,
                                "invert": true
                            }
                        }
                    }
                },
                "seasonId": 0
            },
            { other trades...}
        ]
    }
    ```
    """
    start_point = 0
    query_params = f"?filter=15&start={start_point}"
    url = f"https://api.kickbase.com/v2/leagues/{league_id}/feed{query_params}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }

    ### Send GET request to get the first 30 players of a given user in the given league
    try:
        response = requests.get(url, headers=headers).json()
    except:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.") # TODO: Change exception
    
    user_transfers = []
    ### As long as there are more than 30 entries, we need to send another GET request to get the next 30 entries.
    while response["items"]:
        user_transfers += response["items"]
        start_point += 30
        response = requests.get(f"https://api.kickbase.com/v2/leagues/{league_id}/feed?filter=15&start={start_point}", headers=headers).json()

    return user_transfers