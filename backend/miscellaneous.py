"""
### This module holds all functions and constants that are not related to Kickbase API in any point.

TODO: Maybe list all functions here automatically?
"""

import requests
import json
import logging

import pandas as pd
from datetime import datetime, timedelta, timezone
from os import getenv, path, makedirs
from backend.paths import DATA_DIR, TIMESTAMP_DIR

from backend import exceptions

### ===============================================================================

### Per-run cache for profile pictures. Each lookup downloads the full image, and both
### balances() and league_user_stats_tables() ask for every user.
_profilepic_cache = {}


def clear_caches() -> None:
    """### Empty the per-run caches held in this module."""
    _profilepic_cache.clear()


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

    ### Add start and end points for the graph.
    ### Both are timezone aware UTC, so they line up with the feed timestamps that make
    ### up the rest of the series instead of being shifted by the local timezone.
    for _, data in user_transfer_revenue.items():
        data.append((0, get_start_datetime()))
        data.append((0, datetime.now(timezone.utc)))

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


def get_player_owner(player_stats: dict, league_id: str) -> dict:
    """### Find out which manager owns a player in the given league.

    Kickbase reports ownership per league in the "opl" list, one entry per league the
    player is owned in. The top level "oui" field still exists but is always "0", so it
    cannot be used: checking it classified every player as free.

    Args:
        player_stats (dict): A player_statistics response.
        league_id (str): The league to look up ownership for.

    An entry for the league is present even when nobody owns the player, carrying an
    owner id of "0". Matching on the league alone therefore reports every unowned player
    as owned by "Unknown", so the owner id has to be checked as well.

    Returns:
        dict: The matching "opl" entry, holding the owner id in "oui" and the owner name
            in "onm". None if nobody in this league owns the player.
    """
    for entry in player_stats.get("opl") or []:
        if entry.get("li") != league_id:
            continue

        ### "0", "", None and a missing key all mean nobody owns the player
        owner_id = entry.get("oui")
        if not owner_id or str(owner_id) == "0":
            return None

        return entry

    return None


def get_start_datetime() -> datetime:
    """### Parse the START_DATE environment variable.

    START_DATE is the instant the season started or the league was reset. Activity feed
    events from before it are ignored, so it has to be an exact instant: a league can be
    reset partway through a day.

    Raises:
        exceptions.KickbaseException: If START_DATE is missing or not a valid ISO 8601
            timestamp with an explicit UTC offset.

    Returns:
        datetime: The start instant, as a timezone aware UTC datetime.
    """
    raw = getenv("START_DATE")

    if not raw:
        raise exceptions.KickbaseException(
            "START_DATE is not set. Set it to the instant your season started or your "
            "league was reset, e.g. 2026-08-01T18:00:00Z."
        )

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        raise exceptions.KickbaseException(
            f"START_DATE '{raw}' is not a valid ISO 8601 timestamp. Use e.g. "
            "2026-08-01T18:00:00Z. The old dd.mm.yyyy format is no longer accepted, "
            "because reading it as midnight would silently shift every result."
        )

    ### Without an offset there is no way to tell UTC from local time, and the feed is UTC
    if parsed.tzinfo is None:
        raise exceptions.KickbaseException(
            f"START_DATE '{raw}' has no UTC offset. Add one, e.g. 2026-08-01T18:00:00Z, "
            "so the cutoff cannot shift with the local timezone."
        )

    return parsed.astimezone(timezone.utc)


def parse_feed_timestamp(timestamp: str) -> datetime:
    """### Convert an activity feed timestamp to a timezone aware UTC datetime.

    Args:
        timestamp (str): A feed timestamp, e.g. "2026-08-01T16:43:17Z".

    Returns:
        datetime: The timestamp as a timezone aware UTC datetime.
    """
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(timezone.utc)


def filter_transfers_from(transfers: list, cutoff: datetime) -> list:
    """### Drop activity feed items from before the cutoff.

    Used to ignore events that happened before a league reset. The boundary is
    inclusive: an item exactly on the cutoff is kept.

    Args:
        transfers (list): Activity feed items, each with a "dt" timestamp.
        cutoff (datetime): The timezone aware start instant.

    Returns:
        list: The items at or after the cutoff, in their original order.
    """
    return [item for item in transfers if parse_feed_timestamp(item["dt"]) >= cutoff]


def write_json_to_file(data, file_name: str) -> None:
    """Writes a JSON object to a file.

    Args:
        data (any): data to be written to the file
        file_name (str): file name
    """
    ### Make sure the data directories exist, since app.py can write files before main.py ever ran
    makedirs(TIMESTAMP_DIR, exist_ok=True)

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
    reference_date = datetime(1970, 1, 1)
    converted_date = reference_date + timedelta(days=julian_date)
    return converted_date.strftime("%d.%m.%Y")


def get_profilepic(user_id: str) -> str:
    """### Get the profile picture of a user.

    Cached per user for the duration of the run. Each call downloads the full image, and
    balances() and league_user_stats_tables() both ask for every user.

    Args:
        user_id (str): The user ID.

    Returns:
        str: The URL of the profile picture.
    """
    cache_key = str(user_id)
    if cache_key in _profilepic_cache:
        return _profilepic_cache[cache_key]

    url = f"https://cdn.kickbase.com/files/users/{user_id}/0"
    headers = {
        "Content-Type": "image/jpeg",
    }

    ### Send GET request to get the profile picture
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            profile_pic = response.url # Profile pic is set
        elif response.status_code == 404:
            profile_pic = None # Profile pic is not set
        else:
            response.raise_for_status()
            profile_pic = None
    except requests.exceptions.RequestException as e:
        raise exceptions.NotificatonException("Notification failed! Please check your Discord Webhook URL.") from e

    _profilepic_cache[cache_key] = profile_pic

    return profile_pic