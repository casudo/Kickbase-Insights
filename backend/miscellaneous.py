"""
### This module holds all functions and constants that are not related to Kickbase API in any point.

TODO: Maybe list all functions here automatically?
"""

import requests
import json
import logging

import pandas as pd
from datetime import datetime, timedelta
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

### TYPE (from Activity Feed v4)
# Type 3: New on Transfer Market/Free player listed by Kickbase (Cannot be seen when using Postman?! Only seen in the app (probably because target is set))
# Type 5: User joined the Kickbase league
# Type 15 + data[byr]: User bought player from Kickbase
# Type 15 + data[slr]: User sold player to Kickbase
# Type 15 + data[slr] + data[byr]: User sold player to User
# Type 17: Matchday final points and ranking
# Type 22: Daily Login Bonus
# Type 26: Achievement

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
            if player.id not in taken_player_ids:

                ### Check if position number is valid
                position_nr = player.position
                if position_nr not in POSITIONS:
                    logging.warning(f"Invalid position number: {position_nr} for player {player.firstName} {player.lastName} (PID: {player.id})")
                    position_nr = 1    

                free_players.append({
                    "playerId": player.id,
                    "teamId": player.teamId,
                    "position": POSITIONS[position_nr],
                    "firstName": player.firstName,
                    "lastName": player.lastName,
                    "marketValue": player.marketValue,
                    "trend": player.marketValueTrend,
                    "status": player.status,
                    "points": player.totalPoints,
                })

    logging.info("Got all free players.")

    ### Save to file + timestamp
    write_json_to_file(free_players, "free_players.json")
    write_json_to_file({"time": datetime.now().isoformat()}, "ts_free_players.json")


def calculate_revenue_data_daily(turnovers: dict) -> None:
    """### Calculate daily revenue data.

    Args:
        turnovers (dict): A dictionary containing all buy-sell pairs.
    """
    logging.info("Calculating daily revenue data...")

    ### Load STATIC_users.json
    with open(path.join(DATA_DIR, "STATIC_users.json"), "r") as f:
        league_users = json.load(f)

    ### Create an empty dict with all user names as keys
    user_transfer_revenue = {user_name: [] for user_name in league_users.values()}

    ### This loop iterates over each buy-sell pair in the turnovers list. It calculates the revenue by subtracting the buy value from the sell value.
    ### The revenue and the date of the sell transfer are then appended to the corresponding user's list in user_transfer_revenue.
    
    for buy, sell in turnovers:
        revenue = sell["price"] - buy["price"]
        if buy["user"] in league_users.values():
            user_transfer_revenue[buy["user"]].append((revenue, sell["date"]))

    ### Add start and end points for the graph
    for _, data in user_transfer_revenue.items():
        data.append((0, datetime.strptime(getenv("START_DATE"), "%d.%m.%Y")))
        data.append((0, datetime.now()))

    ### This section converts the data in user_transfer_revenue into Pandas DataFrames.
    ### It performs operations to aggregate daily revenues and calculates cumulative sums.
    ### The resulting DataFrames are stored in the dataframes dictionary.
    dataframes = {}
    for user, data in user_transfer_revenue.items():
        df = pd.DataFrame(data, columns=["revenue", "date"])
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.groupby(pd.Grouper(key="date", freq="D"))["revenue"] \
            .sum().reset_index().sort_values("date")
        df["revenue"] = df["revenue"].cumsum()
        df["date"] = df["date"].dt.strftime("%Y-%m-%d")

        dataframes[user] = df

    ### Here, the data is formatted into a dictionary called data.
    ### Each user's name is a key, and the corresponding value is a list of tuples containing revenue and date information
    data = {user_name: [] for user_name in league_users.values()}
    for user, df in dataframes.items():
        for entry in df.to_numpy().tolist():
            data[user].append((entry[0], entry[1]))

    logging.info("Calculated daily revenue data.")

    ### Save to file + timestamp
    write_json_to_file(data, "revenue_sum.json")
    write_json_to_file({"time": datetime.now().isoformat()}, "ts_revenue_sum.json")


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


def julian_to_date(julian_date: int) -> str:
    """Convert a Julian date to a standard date format (YYYY-MM-DD)."""
    # Assuming the Julian date starts from a known reference date
    # For example, Julian date 0 corresponds to 2000-01-01
    reference_date = datetime(1970, 1, 1)
    converted_date = reference_date + timedelta(days=julian_date)
    return converted_date.strftime("%d.%m.%Y")


def get_profilepic(user_id: str) -> str:
    """### Get the profile picture of a user.

    Args:
        user_id (str): The user ID.

    Returns:
        str: The URL of the profile picture.
    """
    url = f"https://cdn.kickbase.com/files/users/{user_id}/0"
    headers = {
        "Content-Type": "image/jpeg",
    }

    ### Send GET request to get the profile picture
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.url # Profile pic is set
        elif response.status_code == 404:
            return None # Profile pic is not set
        else:
            response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.") from e