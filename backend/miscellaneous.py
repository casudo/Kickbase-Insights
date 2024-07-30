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

### TEAM_IDS
### As of 17.07.2024
# 1 -
# 2 Bayern
# 3 BVB
# 4 Frankfurt
# 5 Freiburg
# 6 - 
# 7 Bayer
# 8 -
# 9 Stuttgart
# 10 Bremen
# 11 Wolfsburg
# 12 -
# 13 Augsburg
# 14 Hoffenheim
# 15 Gladbach
# 16 -
# 17 -
# 18 Mainz
# 19 -
# 20 -
# 21 -
# 22 -
# 23 -
# 24 Bochum
# 25-38 -
# 39 St. Pauli
# 40 Union
# 41 - 
# 42 -
# 43 Leipzig
# 44-49 -
# 50 Heidenheim
# 51 Holstein Kiel
TEAM_IDS = [2, 3, 4, 5, 7, 9, 10, 11, 13, 14, 15, 18, 24, 39, 40, 43, 50, 51]

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
    for team_id in TEAM_IDS:
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

    with open("/code/frontend/src/data/free_players.json", "w") as file:
        file.write(json.dumps(free_players, indent=2))
        logging.debug("Created file free_players.json")

    ### Timestamp for frontend
    with open("/code/frontend/src/data/timestamps/ts_free_players.json", "w") as f:
        f.writelines(json.dumps({'time': datetime.now(tz=TIMEZONE_DE).isoformat()}))
        logging.debug("Created file ts_free_players.json")


def calculate_revenue_data_daily(turnovers, manager):
    """
    ### This function calculates the daily revenue for each user

    The data is stored as dict in JSON file and is later used to create a graph in the frontend.
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
        data.append((0, datetime(2024, 8, 23))) ### TODO: Change Startday at the end of the season ???
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

    ### Finally, the data dictionary is written to a JSON file named 'revenue_sum.json'.
    with open('/code/frontend/src/data/revenue_sum.json', 'w') as f:
        f.writelines(json.dumps(data, indent=2))
        logging.debug("Created file revenue_sum.json")

    ### Timestamp for frontend
    with open("/code/frontend/src/data/timestamps/ts_revenue_sum.json", "w") as f:
        f.writelines(json.dumps({'time': datetime.now(tz=TIMEZONE_DE).isoformat()})) 
        logging.debug("Created file ts_revenue_sum.json")

