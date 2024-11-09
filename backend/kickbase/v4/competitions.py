"""
### This module holds all necessary functions to call Kickbase `/competitions/...` API endpoints.

TODO: Maybe list all functions here automatically?
"""

import requests
import logging
import json

from backend import miscellaneous


def get_teams(token: str) -> dict:
    """### Get all team ids.

    Args:
        token (str): The user's kkstrauth token.

    Returns:
        dict: A dictionary containing all team ids and names.
    """
    logging.info("Getting team ids...")

    url = "https://api.kickbase.com/v4/competitions/1/teams/{team_id}/teamprofile"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }

    active_team_dict = []

    ### Loop through team IDs from 2 to 100
    for team_id in range(2, 101):
        if team_id in [33, 38]:  ### Skip team IDs 33 and 38 cuz they are leading to "500 Internal Server Error"
            continue

        try:
            response = requests.get(url.format(team_id=team_id), headers=headers)
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
            if response.content:  # Check if the response is not empty
                json_response = response.json()
            else:
                logging.warning(f"Empty response for team id {team_id}")
                continue
        except requests.exceptions.RequestException as e:
            logging.warning(f"Failed to get team id {team_id}: {e}")
            continue
        except json.JSONDecodeError as e:
            logging.warning(f"Failed to decode JSON for team id {team_id}: {e}")
            continue
        
        ### Check if team has players
        if json_response["it"]:
            ### Get team id, name, and players
            team_info = {
                "teamId": json_response["tid"],
                "teamName": json_response["tn"],
                "players": json_response["it"]
            }
            active_team_dict.append(team_info)

    logging.info("Got all team ids.")

    ### Save to file
    miscellaneous.write_json_to_file(active_team_dict, "team_ids.json")

    return active_team_dict