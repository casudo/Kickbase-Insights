"""
### This module holds all necessary functions to call Kickbase `/v3/competitions/...` API endpoints.
"""

import requests
import logging
import json


def match_days(token: str, competition_id: int = 1) -> list:
    """### Fetch all matches for every match day in the current season and save to JSON

    Args:
        token (str): The user's kkstrauth token
        competition_id (int): The competition ID (default: 1 which is the Bundesliga)
    
    Returns:
        list: A list of dictionaries containing the match day number, the start date & time of the first match and the last match

    #### Expected response (as of 29.07.24):
    ```json
    {
        "sn": "2024/2025",
        "day": 1,
        "e": [
            {
                "i": "7302",
                "t1": {
                    "i": "15",
                    "sym": "BMG",
                    "n": "M-Gladbach",
                    "g": 0
                },
                "t2": {
                    "i": "7",
                    "sym": "B04",
                    "n": "Bayer 04",
                    "g": 0
                },
                "st": 0,
                "dt": "2024-08-23T18:30:00Z",
                "bo": {
                    "o1": 5.2,
                    "oX": 4.4,
                    "o2": 1.57
                }
            },
            { the other matches for that match day },
        ],
        "nd": 34
    }
    ```
    """
    base_url = f"https://api.kickbase.com/v3/competitions/{competition_id}/matches"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }

    match_days = []

    logging.info("Fetching match days...")

    ### Assuming the maximum number of match days is 34
    for match_day_nr in range(1, 35):
        url = f"{base_url}?matchDay={match_day_nr}"

        try:
            response = requests.get(url, headers=headers).json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed for match day {match_day_nr}: {e}")
            continue

        if response["e"]:
            first_match = response["e"][0]["dt"] ### Start date & time of the first match
            last_match = response["e"][-1]["dt"] ### Start date & time of the last match

            match_days.append({
                "day": response["day"],
                "firstMatch": first_match,
                "lastMatch": last_match,
            })

    logging.info("Match days fetched.")

    ### Save the match days data to a JSON file
    with open("/code/frontend/src/data/match_days.json", "w") as f:
        f.write(json.dumps(match_days, indent=2))
        logging.debug("Created file match_days.json")

    ### TODO: Timestamp needed here?

    return match_days