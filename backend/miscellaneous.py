"""
### This module holds all functions and constants that are not related to Kickbase API in any point.

TODO: Maybe list all functions here automatically?
"""

import requests
import json
import pytz
import logging

import pandas as pd
from datetime import datetime
from os import getenv, path
from main import DATA_DIR, TIMESTAMP_DIR

from backend import exceptions
from backend.kickbase.v1 import competition

### ===============================================================================

POSITIONS = {1: "TW", 2: "ABW", 3: "MF", 4: "ANG"}
### 0 = Vereinslos oder sehr neue Spieler in der Liga

### TREND (can be found via player stats)
# 0: Gleichbleibend (500k player) (Welcher Zeitraum?)
# 1: Steigt
# 2: Sinkt
### Conversion from number to icon for the frontend in "SharedConstants.js"

### STATUS (can be found via player stats)
# 0: Fit (Green Checkmark)
# 1: Verletzt (Red Cross)
# 2: Angeschlagen (bandage)
# 4: Aufbautraining (Orange Cone)
# 8: Rote Karte (Red Card)
# 32: 5. Gelbe Karte (Yellow Card)
# 128: Raus aus der Liga (Red Arrow)
# 256: Abwesend (Grey Clock)
### Conversion from number to icon for the frontend in "SharedConstants.js"

### TYPE (from league feed)
# Type 2: Verkauft an Kickbase
# Type 2 + meta[bn]: Verkauft an Spieler (bn = buyerName)
# Type 3: Free player listed by Kickbase
# Type 8: Final matchday points
# Type 12: Gekauft von Kickbase

### TYPE (from v2 League Feed)
# Type 3: Free player listed by Kickbase
# Type 5: User joined the Kickbase league
# Type 15 + meta["s"]: User sold Player to Kickbase
# Type 15 + meta["b"]: User bought Player from Kickbase
# Type 15 + meta["s"] + meta["b"]: User sold Player to User
# Type 16: News from Kickbase?

TIMEZONE_DE = pytz.timezone("Europe/Berlin")

### ===============================================================================

def discord_notification(title: str, message: str, color: int, webhook_url: str) -> None:
    """### Send a Discord notification to a webhook.

    Args:
        title (str): Title of the notification.
        message (str): Message of the notification.
        color (int): Color of the notification.
        webhook_url (str): Webhook URL to send the notification to.

    Raises:
        WIP! TODO!
    """
    url = webhook_url
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
    

def get_free_players(token: str, taken_players: list) -> None:
    """### Get all free players based on the taken players.

    Args:
        token (str): The user's kkstrauth token.
        taken_players (list): A list of all taken players.

    Returns:
        None
    """
    logging.info("Getting free players...")

    free_players = []

    ### Get all taken player ids
    taken_player_ids = [player["playerId"] for player in taken_players]

    ### Cycle through all teams and get the players who are not taken
    for team_id in get_team_ids(token):
        ### Cycle through all players of the team
        for player in competition.team_players(token, team_id):
            ### Check if the player is not taken
            if player.p.id not in taken_player_ids:

                ### Check if position number is valid
                position_nr = player.p.position
                if position_nr not in POSITIONS:
                    logging.warning(f"Invalid position number: {position_nr} for player {player.p.firstName} {player.p.lastName} (PID: {player.p.id})")
                    position_nr = 1    

                free_players.append({
                    "playerId": player.p.id,
                    "teamId": player.p.teamId,
                    "position": POSITIONS[position_nr],
                    "firstName": player.p.firstName,
                    "lastName": player.p.lastName,
                    "marketValue": player.p.marketValue,
                    "trend": player.p.marketValueTrend,
                    "status": player.p.status,
                    "points": player.p.totalPoints,
                })

    logging.info("Got all free players.")

    ### Save to file + timestamp
    write_json_to_file(free_players, "free_players.json")
    write_json_to_file({"time": datetime.now(tz=TIMEZONE_DE).isoformat()}, "ts_free_players.json")

def calculate_revenue_data_daily(turnovers: dict, manager: list) -> None:
    """### Calculate daily revenue data.

    Args:
        turnovers (dict): A dictionary containing all buy-sell pairs.
        manager (list): A list of all users in the Kickbase league.
    """
    logging.info("Calculating daily revenue data...")

    ### Create an empty dict with all users as keys
    user_transfer_revenue = {user["name"]: [] for user in manager}

    ### This loop iterates over each buy-sell pair in the turnovers list. It calculates the revenue by subtracting the buy value from the sell value.
    ### The revenue and the date of the sell transfer are then appended to the corresponding user's list in user_transfer_revenue.
    
    for buy, sell in turnovers:
        revenue = sell['price'] - buy['price']
        user_transfer_revenue[buy['user']].append((revenue, sell['date']))

    ### Add start and end points for the graph
    for _, data in user_transfer_revenue.items():
        data.append((0, datetime.strptime(getenv("START_DATE"), "%d.%m.%Y")))
        data.append((0, datetime.now()))

    ### This section converts the data in user_transfer_revenue into Pandas DataFrames.
    ### It performs operations to aggregate daily revenues and calculates cumulative sums.
    ### The resulting DataFrames are stored in the dataframes dictionary.
    dataframes = {}
    for user, data in user_transfer_revenue.items():
        df = pd.DataFrame(data, columns=['revenue', 'date'])
        df['date'] = pd.to_datetime(df['date'], utc=True)
        df = df.groupby(pd.Grouper(key='date', freq='D'))['revenue'] \
            .sum().reset_index().sort_values('date')
        df['revenue'] = df['revenue'].cumsum()
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')

        dataframes[user] = df

    ### Here, the data is formatted into a dictionary called data.
    ### Each user's name is a key, and the corresponding value is a list of tuples containing revenue and date information
    data = {user["name"]: [] for user in manager}
    for user, df in dataframes.items():
        for entry in df.to_numpy().tolist():
            data[user].append((entry[0], entry[1]))

    logging.info("Calculated daily revenue data.")

    ### Save to file + timestamp
    write_json_to_file(data, "revenue_sum.json")
    write_json_to_file({"time": datetime.now(tz=TIMEZONE_DE).isoformat()}, "ts_revenue_sum.json")


def get_team_ids(token: str) -> dict:
    """### Get all team ids.

    Args:
        token (str): The user's kkstrauth token.

    Returns:
        dict: A dictionary containing all team ids and names.
    """
    logging.info("Getting team ids...")

    url = "https://api.kickbase.com/competition/teams/{team_id}/players"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": f"kkstrauth={token};",
    }

    ### Dictionary to store team IDs and names
    team_id_dict = {}

    ### Loop through team IDs from 1 to 100
    for team_id in range(1, 101):
        try:
            response = requests.get(url.format(team_id=team_id), headers=headers).json()
        except:
            raise exceptions.NotificatonException("Failed to get team ids.")
        
        if response.get("p"): ### If list p[] is not empty
            ### Get the first player to extract team information
            team_id = response["p"][0]["teamId"]
            team_name = response["p"][0]["teamName"]
            team_id_dict[team_id] = team_name

    logging.info("Got all team ids.")

    ### Save to file
    write_json_to_file(team_id_dict, "team_ids.json")

    return team_id_dict


def write_json_to_file(data, file_name: str) -> None:
    """Writes a JSON object to a file.

    Args:
        data (any): data to be written to the file
        file_name (str): file name
    """
    ### Check if it is a data or timestamp file
    try:
        if file_name.startswith("ts_"):
            file_path = path.join(TIMESTAMP_DIR, file_name)
            with open(file_path, "w") as f:
                json.dump(data, f)
            logging.debug(f"Created timestamp file {file_name}")
        else:
            file_path = path.join(DATA_DIR, file_name)
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            logging.debug(f"Created file {file_name}")
    except Exception as e:
        logging.error(f"Failed to write JSON to {file_path}: {e}")