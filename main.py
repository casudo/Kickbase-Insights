import json
import time
import logging

from os import getenv, makedirs, path, getcwd
from art import tprint
from sys import stdout
from logging.config import dictConfig
from datetime import datetime, timedelta

from backend import exceptions, miscellaneous
from backend.kickbase.v4 import competitions, user, leagues

### -------------------------------------------------------------------
### -------------------------------------------------------------------
### -------------------------------------------------------------------

__version__ = getenv("REACT_APP_VERSION", "Warning: Couldn't load version")

### Get the current working directory dynamically
BASE_PATH = getcwd()
### Paths for logs and data files
LOG_DIR = path.join(BASE_PATH, "logs")
DATA_DIR = path.join(BASE_PATH, "frontend", "src", "data")
TIMESTAMP_DIR = path.join(DATA_DIR, "timestamps")


def main() -> None:
    """### This is the main function of the Kickbase Insights program.

    It performs various tasks related to logging, user login, and data retrieval from the Kickbase API.
    """
    ### Ensure directories exist
    makedirs(LOG_DIR, exist_ok=True)
    makedirs(TIMESTAMP_DIR, exist_ok=True)

    ### Define the log file paths
    log_file_path = path.join(LOG_DIR, "kickbase-insights.log")
    verbose_log_file_path = path.join(LOG_DIR, "kickbase-insights-verbose.log")

    ### Set logging settings for the Python logging module
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "[L] {asctime} [{levelname}] {pathname} - Line {lineno} - {message}",
                "style": "{",
                "datefmt": "%d.%m.%Y %H:%M:%S",
            },
            "simple": {
                "format": "[L] {asctime} [{levelname}] - {message}",
                "style": "{",
                "datefmt": "%d.%m.%Y %H:%M:%S",
            },
        },
        "handlers": {
            "file": { # Log only INFO and higher to file (simple format)
                "level": "INFO",
                "class": "logging.handlers.TimedRotatingFileHandler",
                "filename": log_file_path,
                "when": "D",
                "interval": 30, # overwrite interval in days
                "backupCount": 0, # don't keep any backups
                "formatter": "simple",
                "encoding": "utf-8",
            },
            "verbose_file": { # Log EVERYTHING to file (verbose format)
                "level": "DEBUG",
                "class": "logging.handlers.TimedRotatingFileHandler",
                "filename": verbose_log_file_path,
                "when": "D",
                "interval": 14, # overwrite interval in days
                "backupCount": 0, # don't keep any backups
                "formatter": "verbose",
                "encoding": "utf-8",
            },
            "console": { # Log only INFO and higher to console (simple format)
                "level": "INFO",
                "class": "logging.StreamHandler",
                "stream": stdout,
                "formatter": "simple",
            },
        },
        "loggers": {
            "root": { # "Root" logger: Send all logging entries to the handlers
                "handlers": ["file", "verbose_file", "console"],
                "level": "DEBUG",
                "propagate": True,
            },
        },
    }
    ### Configure logging with the settings from the dictionary
    dictConfig(LOGGING)

    try:
        selected_league, user_token = login()

        ### Get the daily login gift in every available league
        get_gift(user_token)

        market(user_token, selected_league)
        market_value_changes(user_token, selected_league)

        taken_free_players(user_token, selected_league)

        balances(user_token, selected_league)

        turnovers(user_token, selected_league)

        team_value_per_match_day(user_token, selected_league)

        league_user_stats_tables(user_token, selected_league)

        # live_points(user_token, selected_league) # needs to be run first to initialize the live_points.json file
    except exceptions.LoginException as e:
        print(e)
        return
    except exceptions.NotificatonException as e:
        print(e)
        return
    except exceptions.KickbaseException as e:
        print(e)
        return
    

def login() -> tuple:
    """### Logs in to Kickbase and gathers various information.

    Returns:
        tuple: A tuple containing the following elements:
            -- selected_league (object): The league the user wants to get data from for the frontend.
            -- user_token (str): User token for authentication.
    """
    logging.info("Logging in...")

    ### Login to Kickbase using the credentials from the environment variables
    user_info, user_token = user.login(kb_mail, kb_password, discord_webhook)
    logging.info(f"Successfully logged in as {user_info.name}")

    ### Get all leagues the user is in
    league_list = leagues.get_league_list(user_token)
    if not league_list:
        logging.error("No leagues found. Exiting...")
        exit()
    logging.info(f"Available leagues: {', '.join([league.name for league in league_list])}") # Print all available leagues the user is in

    ### Fetch the preferred league name from the environment variable
    preferred_league_name = getenv("KB_LIGA")

    ### Initialize selected_league to None
    ### The selected_league will be the league the user wants to get the data from for the frontend
    selected_league = None

    ### Filter league_list to find the preferred league, default to the first league if not found
    if preferred_league_name:
        for league in league_list:
            if league.name == preferred_league_name:
                selected_league = league
                logging.info(f"Preferred league '{preferred_league_name}' found: {selected_league.name}")
                break
        if not selected_league:
            logging.warning(f"Preferred league '{preferred_league_name}' not found. Defaulting to the first league: {league_list[0].name}")
            selected_league = league_list[0]
    else:
        logging.info(f"No preferred league set. Using the first league in the list: {league_list[0].name}")
        selected_league = league_list[0]

    return selected_league, user_token


def get_gift(user_token: str) -> None:
    """### Collect the daily login gift in every available league.

    Args:
        user_token (str): The user's kkstrauth token.
    """
    gift = user.collect_gift(user_token)

    ### Check if response["it"] is not empty:
    if gift["it"]:
        logging.info(f"Gift available in league {gift['it'][0]['lnm']}!")
        miscellaneous.discord_notification("Kickbase Gift available!", f"Amount: {gift['it'][0]['v']}\nLevel: {gift['it'][0]['day']}", 6617600, discord_webhook) # TODO: Change color
    else:
        logging.info("Gift has already been collected!")


def market(user_token: str, selected_league: object) -> None:
    """### Retrieves all players listed on the transfer market.

    Args:
        user_token (str): The user's kkstrauth token.
        selected_league (object): The league the user wants to get data from for the frontend.
    """
    logging.info("Getting players listed on transfer market...")

    ### Get all players on the market
    players_on_market = leagues.get_market(user_token, selected_league.id)

    players_listed_by_user = []
    players_listed_by_kickbase = []

    for player in players_on_market:
        if player.position not in miscellaneous.POSITIONS:
            logging.warning(f"Invalid position number: {player.position} for player {player.firstName} {player.lastName} (PID: {player.id})")
            player.position = 1 ### Default to "Torwart" (Goalkeeper)
        
        player_info = {
            "teamId": player.teamId,
            "position": miscellaneous.POSITIONS[player.position],
            "firstName": f"{player.firstName}", 
            "lastName": f"{player.lastName}",
            "price": player.price,
            "status": player.status,
            "trend": player.marketValueTrend,
            "expiration": (datetime.now() + timedelta(seconds=player.expiry)).strftime('%d.%m.%Y %H:%M:%S'),
        }
        
        ### Check if player is listed by user or Kickbase
        if not player.username:
            players_listed_by_kickbase.append(player_info)
            logging.debug(f"Player {player.firstName} {player.lastName} is listed by Kickbase!")
        else:
            player_info["seller"] = player.username
            players_listed_by_user.append(player_info)
            logging.debug(f"Player {player.firstName} {player.lastName} is listed by {player.username}!")

    logging.info("Got all players listed on transfer market.")

    ### Save to file + timestamp
    miscellaneous.write_json_to_file(players_listed_by_user, "market_user.json")
    miscellaneous.write_json_to_file({"time": datetime.now().isoformat()}, "ts_market_user.json")

    ### Save to file + timestamp
    miscellaneous.write_json_to_file(players_listed_by_kickbase, "market_kickbase.json")
    miscellaneous.write_json_to_file({"time": datetime.now().isoformat()}, "ts_market_kickbase.json")


def market_value_changes(user_token: str, selected_league: object) -> None:
    """### Retrieves the market value changes for all players in the league.

    Args:
        user_token (str): The user's kkstrauth token.
        selected_league (object): The league the user wants to get data from for the frontend.
    """
    logging.info("Getting market value changes for all players...")

    players_LIST = []

    user_list = leagues.get_users(user_token, selected_league.id)
    ### Create a dictionary to map user IDs to user names
    user_id_to_name = {user["i"]: user["n"] for user in user_list}

    all_teams_in_competition = competitions.get_team_overview(user_token)

    ### Loop through all teams
    for team in all_teams_in_competition:
        ### Loop through all players in the team
        for player in team["players"]:
            ### Get the market value changes for the player
            player_stats = leagues.player_statistics(user_token, selected_league.id, player["i"])
            player_marketvalue = leagues.player_marketvalue(user_token, selected_league.id, player["i"])

            ### Check if player is owned by user
            if player_stats["oui"] != "0":  # "oui" = "ownedUserId"
                manager = user_id_to_name.get(player_stats["oui"], "Unknown")
            else:
                manager = "Kickbase"
                
            ### Check if position number is valid
            if player["pos"] not in miscellaneous.POSITIONS:
                logging.warning(f"Invalid position number: {player_stats['pos']} for player {player_stats['fn']} {player_stats['ln']} (PID: {player_stats['i']})")
                player["pos"] = 1 # Default to "Torwart" (Goalkeeper)

            ### Create a custom json dict for every player
            players_LIST.append({
                "teamId": player_stats["tid"],
                "position": miscellaneous.POSITIONS[player_stats["pos"]],
                "firstName": player_stats.get("fn", None), 
                "lastName": player_stats["ln"], 
                "marketValue": player_stats["mv"],
                "today": player_marketvalue[-1]["mv"] - player_marketvalue[-2]["mv"],
                "yesterday": player_marketvalue[-2]["mv"] - player_marketvalue[-3]["mv"],
                "twoDays": player_marketvalue[-3]["mv"] - player_marketvalue[-4]["mv"],
                "sevenDaysAvg": player_marketvalue[-1]["mv"] - player_marketvalue[-8]["mv"] if len(player_marketvalue) >= 8 else None,
                "thirtyDaysAvg": player_marketvalue[-1]["mv"] - player_marketvalue[-31]["mv"] if len(player_marketvalue) >= 31 else None,
                "manager": manager,
            })
            logging.debug(f"Player {player_stats.get('fn', None)} {player_stats['ln']} has a market value of {player_stats['mv']} and is owned by {manager}.")

    logging.info("Got all market value changes for all players.")

    ### Save to file + timestamp
    miscellaneous.write_json_to_file(players_LIST, "market_value_changes.json")
    miscellaneous.write_json_to_file({"time": datetime.now().isoformat()}, "ts_market_value_changes.json")


def taken_free_players(user_token: str, selected_league: object):
    """### Retrieves all taken and free players in the league.

    Args:
        user_token (str): The user's kkstrauth token.
        selected_league (object): The league the user wants to get data from for the frontend.
    """
    logging.info("Getting taken and free players...")

    taken_players = []
    free_players = []

    ### Get all users in the league
    with open(path.join(DATA_DIR, "STATIC_users.json"), "r") as f:
        league_users = json.load(f)

    ### Get all transfers in the league
    all_transfers = leagues.transfers(user_token, selected_league.id)

    ### Create a dictionary to store buy prices from transfers
    buy_prices = {}
    for transfer in all_transfers:
        if "byr" in transfer["data"]:
            user_id = {value: key for key, value in league_users.items()}.get(transfer["data"]["byr"]) # Reverse mapping from user name to user ID
            player_id = transfer["data"]["pi"]
            buy_price = transfer["data"]["trp"]

            if user_id not in buy_prices:
                buy_prices[user_id] = []
            
            buy_prices[user_id].append((player_id, buy_price))

    ### Cycle through all teams
    with open(path.join(DATA_DIR, "STATIC_teams.json"), "r") as f:
        all_teams = json.load(f)
    for team in all_teams:
        ### Cycle through all players of the team
        for player in team["players"]:

            ### Search the stats of the given player ID to fill the missing attributes for the player
            player_stats = leagues.player_statistics(user_token, selected_league.id, player["i"])

            ### Check if the player is owned by a user
            if player_stats["oui"] != "0":  # "oui" = "ownedUserId"
                logging.debug(f"Player {player_stats.get('fn', None)} {player['n']} is owned by user {league_users.get(player_stats['oui'], 'Unknown')}!")

                ### Check if position number is valid
                if player["pos"] not in miscellaneous.POSITIONS:
                    logging.warning(f"Invalid position number: {player['pos']} for player {player_stats.get('fn', None)} {player['n']} (PID: {player['i']})")
                    player["pos"] = 1 ### Default to "Torwart" (Goalkeeper)

                ### Determine the buy price
                current_user_id = player_stats["oui"]
                buy_price = 0
                if current_user_id in buy_prices:
                    for pid, price in buy_prices[current_user_id]:
                        if pid == player["i"]:
                            buy_price = price
                            break

                ### TODO: Find a way to get the marketValue on user join date (START_DATE) or leave it as 0
                # if buy_price == 0:
                #     ### Set the buyPrice to the first entry in the player_marketvalues list
                #     ### NOTE: THe first entry might be at a later date than the start of the season!!
                #     ### e.g. START_DATE = 16.07.24, but the first entry in the player_marketvalues list is at 10.08.24
                #     ### This isn't a great solution, so it's WIP for now
                #     start_date = getenv("START_DATE")

                #     player_marketvalues = leagues.player_marketvalue(user_token, selected_league.id, player["i"])

                #     for marketValue in player_marketvalues:
                #         ### Convert the Julian date to a standard date
                #         market_value_date = miscellaneous.julian_to_date(marketValue["dt"]) # 10.08.24  -erster Eintrag

                #         if market_value_date == start_date:
                #             buy_price = marketValue["mv"]
                #             logging.debug(f"Player {player_stats.get('fn', None)} {player['n']} was assigned at the start of the season. Market value on START_DATE {start_date}: {buy_price}€.")
                #             break

                ### Create a custom json dict for every taken player. This will be passed to the frontend later.
                taken_players.append({
                    "owner": league_users.get(player_stats["oui"], "Unknown"),
                    "playerId": player["i"],
                    "teamId": player["tid"],
                    "position": miscellaneous.POSITIONS[player["pos"]],
                    "firstName": player_stats.get("fn", None),
                    "lastName": player["n"],
                    "buyPrice": buy_price,
                    "marketValue": player["mv"],
                    "status": player["st"],
                    "trend": player["mvt"],
                })
            else:
                ### Create a custom json dict for every free player. This will be passed to the frontend later.
                free_players.append({
                    "playerId": player["i"],
                    "teamId": player["tid"],
                    "position": miscellaneous.POSITIONS[player["pos"]],
                    "firstName": player_stats.get("fn", None),
                    "lastName": player["n"],
                    "marketValue": player["mv"],
                    "points": player_stats.get("tp", 0),
                    "status": player["st"],
                    "trend": player["mvt"],
                })

    logging.info("Got all taken and free players.")
    
    ### Save to file + timestamp
    miscellaneous.write_json_to_file(taken_players, "taken_players.json")
    miscellaneous.write_json_to_file({"time": datetime.now().isoformat()}, "ts_taken_players.json")

    ### Save to file + timestamp
    miscellaneous.write_json_to_file(free_players, "free_players.json")
    miscellaneous.write_json_to_file({"time": datetime.now().isoformat()}, "ts_free_players.json")


def turnovers(user_token: str, selected_league: object) -> None:
    """### Retrieves all turnovers in the league.

    Args:
        user_token (str): The user's kkstrauth token.
        selected_league (object): The league the user wants to get data from for the frontend.
    """
    logging.info("Getting turnovers...")

    final_turnovers = []

    ### Load existing transfers from all_transfers.json which were saved in earlier runs
    all_transfers_path = path.join(DATA_DIR, "all_transfers.json")

    all_transfers = [] # Initialize as empty list first

    ### Check if all_transfers.json exists and load it
    if path.exists(all_transfers_path):
        try:
            with open(all_transfers_path, "r") as f:
                all_transfers = json.load(f)
            logging.debug(f"Loaded {len(all_transfers)} existing transfers from all_transfers.json")
        except json.JSONDecodeError:
            logging.warning(f"The file {all_transfers_path} is empty or contains invalid JSON. Initializing all_transfers as an empty list.")
    else:
        logging.debug(f"The file {all_transfers_path} does not exist. Initializing all_transfers as an empty list.")

    ### Get new transfers from the API
    new_transfers = leagues.transfers(user_token, selected_league.id)
    logging.debug(f"Found {len(new_transfers)} current transfers from the API")

    ### Append only new transfers (ignoring duplicates)
    current_transfer_ids = {item["i"] for item in all_transfers}  # Set of existing transfer IDs
    for transfer in new_transfers:
        if transfer["i"] not in current_transfer_ids:  # Check if the transfer is new
            all_transfers.append(transfer)
            current_transfer_ids.add(transfer["i"])  # Update the set to include the new transfer

    ### Sort transfers by date after appending new ones
    all_transfers.sort(key=lambda x: datetime.fromisoformat(x["dt"].replace("Z", "")))

    logging.debug(f"Total transfers after appending new ones: {len(all_transfers)}")

    ### Save updated transfers back to all_transfers.json
    miscellaneous.write_json_to_file(all_transfers, "all_transfers.json")
    logging.debug("Updated all_transfers.json with new transfers")

    ### Process the transfers as usual
    transfers = []

    ### Process each transfer item
    for item in all_transfers:
        ### Determine the transfer type based on the type and metadata
        if item["t"] == 15:
            if "slr" in item["data"] and "byr" in item["data"]:
                transfer_type = "sell"
                user = item["data"]["slr"]
                trade_partner = item["data"]["byr"]
            elif "slr" in item["data"]:
                transfer_type = "sell"
                user = item["data"]["slr"]
                trade_partner = "Kickbase"
            elif "byr" in item["data"]:
                transfer_type = "buy"
                user = item["data"]["byr"]
                trade_partner = "Kickbase"
            else:
                transfer_type = "unknown"
        else:
            transfer_type = "unknown"

        ### Search the stats of the given player ID to fill the missing attributes for the player
        player_stats = leagues.player_statistics(user_token, selected_league.id, item["data"]["pi"])

        ### Create a custom json dict for every transfer
        transfers.append({
            "date": item["dt"],
            "type": transfer_type,
            "user": user,
            "tradePartner": trade_partner,
            "price": item["data"]["trp"],
            "playerId": item["data"]["pi"],
            "teamId": item["data"]["tid"],
            "firstName": player_stats.get("fn", None),
            "lastName": player_stats["ln"],
        })

    ### Removes duplicates given by the API (probably not needed since v4)
    transfers = list({frozenset(item.items()): item for item in transfers}.values())

    turnovers = []

    ### Iterate over every element in the "transfers" list (where "i" is the index) and save it to "buy_transfer"
    for i, buy_transfer in enumerate(transfers):
        ### Skip if the transfer is type "sell"
        if buy_transfer["type"] == "sell":
            continue

        ### This nested loop iterates over the remaining transfers (starting from the current buy transfer).
        ### It compares each of these transfers with the current buy transfer
        for sell_transfer in transfers[i:]:
            if sell_transfer["type"] == "buy":
                continue

            ### This condition checks if the player ID of the current sell transfer matches the player ID of the current buy transfer. 
            ### If there is a match, it means a corresponding buy-sell pair is found.
            if sell_transfer["playerId"] == buy_transfer["playerId"]:
                turnovers.append((buy_transfer, sell_transfer))
                break

    ### Revenue generated by randomly assigned players
    for transfer in transfers:
        ### Skip buy transfers
        if transfer["type"] == "buy":
            continue

        ### This condition checks if the current sell transfer is not already part of a buy-sell pair in the turnovers list.
        if transfer not in [turnover[1] for turnover in turnovers]:

            ### TODO: Find a way to get the marketValue on user join date (START_DATE) or leave it as 0
            # ### Search the stats of the given player ID to fill the missing attributes for the player
            # player_stats = leagues_v1.player_statistics(user_token, selected_league.id, transfer["playerId"])

            # ### Loop through all marketValues of the player until the "day" matches the START_DATE
            # start_date = datetime.strptime(getenv("START_DATE"), "%d.%m.%Y").date()

            # for marketValue in player_stats["marketValues"]:
            #     ### Normalize the marketValue date to date only
            #     market_value_date = datetime.fromisoformat(marketValue["d"].replace("Z", "")).date()

            #     if market_value_date == start_date:
            #         price = marketValue["m"]
            #         logging.debug(f"Starter player {transfer['firstName']} {transfer['lastName']} was sold! Market value on START_DATE {start_date}: {price}€.")
            #         break

            price = 0
            logging.debug(f"Starter player {transfer['firstName']} {transfer['lastName']} was sold! Buy price will be set to 0€.")

            ### If an unmatched sell transfer is found, a simulated buy transfer is created with some default values
            date = datetime.strptime(getenv("START_DATE"), "%d.%m.%Y").isoformat()
            buy_transfer = {"date": date,
                            "type": "assigned_at_start",
                            "user": transfer["user"],
                            "tradePartner": "Kickbase",
                            "price": price,
                            "playerId": transfer["playerId"],
                            "teamId": transfer["teamId"],
                            "firstName": transfer["firstName"],
                            "lastName": transfer["lastName"],
                        }

            turnovers.append((buy_transfer, transfer))

    final_turnovers += turnovers

    logging.info("Got all turnovers.")

    ### Save to file + timestamp
    miscellaneous.write_json_to_file(final_turnovers, "turnovers.json")
    miscellaneous.write_json_to_file({"time": datetime.now().isoformat()}, "ts_turnovers.json")

    ### Calculate revenue data for the graph
    miscellaneous.calculate_revenue_data_daily(final_turnovers)


def team_value_per_match_day(user_token: str, selected_league: object) -> None:
    """### Calculates the team value per match day for all users in the league.

    Args:
        user_token (str): The user's kkstrauth token.
        selected_league (object): The league the user wants to get data from for the frontend.
    """
    logging.info("Calculating team value per match day...")

    final_team_value = {}

    ### Get all match days of the season
    current_match_day, match_days_list = competitions.match_days(user_token)
    
    ### Loop through all users in the league
    with open(path.join(DATA_DIR, "STATIC_users.json"), "r") as f:
        league_users = json.load(f)
    for user_id, user_name in league_users.items():
        ### Get the team value for each match day
        team_value = {match_day: 0 for match_day in range(1, current_match_day + 1)}
    
        ### Loop through all match days
        for match_day in match_days_list:
            ### Skip processing if the match day is in the future
            if match_day["day"] > current_match_day:
                continue
        
            ranking_data = leagues.ranking(user_token, selected_league.id, match_day["day"])
            team_value_on_match_day = None

            for real_user in ranking_data["us"]:
                if real_user["i"] == user_id:
                    team_value_on_match_day = real_user["tv"]
                    break
        
            if len(team_value) >= match_day["day"]:
                team_value[match_day["day"]] = team_value_on_match_day
        
        final_team_value[user_name] = team_value

    logging.info("Calculated team value per match day.")

    ### Save to file + timestamp
    miscellaneous.write_json_to_file(final_team_value, "team_values.json")
    miscellaneous.write_json_to_file({"time": datetime.now().isoformat()}, "ts_team_values.json")


def league_user_stats_tables(user_token: str, selected_league: object) -> None:
    """### Retrieves the statistics for all users in the league.

    Args:
        user_token (str): The user's kkstrauth token.
        selected_league (object): The league the user wants to get data from for the frontend.
    """
    logging.info("Getting league user stats...")

    final_user_stats = []

    ### Loop through all users in the league
    with open(path.join(DATA_DIR, "STATIC_users.json"), "r") as f:
        league_users = json.load(f)
    for user_id, user_name in league_users.items():
        ### Get stats for each user
        user_stats = leagues.user_stats(user_token, selected_league.id, user_id)

        ### Create a custom json dict for every user
        final_user_stats.append({
            ### Shared stats 
            "userId": user_id,
            "userName": user_name,
            "profilePic": miscellaneous.get_profilepic(user_id),
            "mdWins": user_stats["mdw"],
            "maxPoints": leagues.battles(user_token, selected_league.id, 8)["us"][0]["v"],
            ### Stats for "Liga -> Tabelle" ONLY
            "placement": user_stats["pl"],
            "points": user_stats["tp"],
            "teamValue": user_stats["tv"],
            # "maxBuyPrice": user_stats["leagueUser"]["maxBuyPrice"],
            # "maxBuyFirstName": user_stats["leagueUser"]["maxBuyFirstName"],
            # "maxBuyLastName": user_stats["leagueUser"]["maxBuyLastName"],
            # "maxSellPrice": user_stats["leagueUser"]["maxSellPrice"],
            # "maxSellFirstName": user_stats["leagueUser"]["maxSellFirstName"],
            # "maxSellLastName": user_stats["leagueUser"]["maxSellLastName"]
            ### Stats for "Liga -> Saison Statistiken" ONLY
            "avgPoints": user_stats["ap"],
            # "minPoints": get_season_stat(user_stats, "minPoints"),
            # "bought": get_season_stat(user_stats, "bought"),
            # "sold": get_season_stat(user_stats, "sold"),
            "trades": user_stats["t"],
            ### Stats for "Liga -> Battles" ONLY
            "pointsGoalKeeper": leagues.battles(user_token, selected_league.id, 4)["us"][0]["v"],
            "pointsDefenders": leagues.battles(user_token, selected_league.id, 5)["us"][0]["v"],
            "pointsMidFielders": leagues.battles(user_token, selected_league.id, 6)["us"][0]["v"],
            "pointsForwards": leagues.battles(user_token, selected_league.id, 7)["us"][0]["v"],
            # "avgGoalKeeper": user_stats["seasons"][0]["averageGoalKeeper"],
            # "avgDefenders": user_stats["seasons"][0]["averageDefenders"],
            # "avgMidFielders": user_stats["seasons"][0]["averageMidFielders"],
            # "avgForwards": user_stats["seasons"][0]["averageForwards"],
        })            

    logging.info("Got league user stats.")

    ### Save to file + timestamp
    miscellaneous.write_json_to_file(final_user_stats, "league_user_stats.json")
    miscellaneous.write_json_to_file({"time": datetime.now().isoformat()}, "ts_league_user_stats.json")


def live_points(user_token: str, selected_league: object) -> None:
    """### Retrieves the live points for the players in a users team.

    Args:
        user_token (str): The user's kkstrauth token.
        selected_league (object): The league the user wants to get data from for the frontend.
    """
    logging.info("Getting live points...")

    ### Get the current live points
    live_points = leagues_v1.live_points(user_token, selected_league.id)

    ### Create a custom json dict for every user and his players
    final_live_points = []

    for real_user in live_points["u"]:
        ### Create a custom json dict for every player of the user
        players = []

        for player in real_user["pl"]:
            players.append({
                "playerId": player["id"],
                "teamId": player["tid"],
                "firstName": player.get("fn", ""),
                "lastName": player["n"],
                "number": player["nr"],
                "points": player["t"],
                "goals": player["g"],
                "assists": player["a"],
                "redCards": player["r"],
                "yellowCards": player["y"],
                "yellowRedCards": player["yr"],
                ### Custom attributes for the frontend
                "fullName": f"{player.get('fn', '')} {player['n']} ({player['nr']})",
            })

        final_live_points.append({
            "userId": real_user["id"],
            "userName": real_user["n"],
            "livePoints": real_user["t"],
            "totalPoints": real_user["st"],
            "players": players,
        })

    logging.info("Got live points.")

    ### Save to file + timestamp
    miscellaneous.write_json_to_file(final_live_points, "live_points.json")
    miscellaneous.write_json_to_file({"time": datetime.now().isoformat()}, "ts_live_points.json")


def balances(user_token: str, selected_league: object) -> None:
    """### Retrieves the estiamted balances for all users in the league. Daily login bonus and money from achievements are not considered.

    Args:
        user_token (str): The user's kkstrauth token.
        selected_league (object): The league the user wants to get data from for the frontend.
    """
    logging.info("Getting balances...")

    initial_balance = float(getenv("START_MONEY", 50000000))
    final_balances = []

    ### Get all transfers from the API
    all_transfers = leagues.transfers(user_token, selected_league.id)
    logging.debug(f"Found {len(all_transfers)} transfers in total")

    ### Initialize user balances
    with open(path.join(DATA_DIR, "STATIC_users.json"), "r") as f:
        league_users = json.load(f)
        user_balances = {user_id: initial_balance for user_id, user_name in league_users.items()}

    ### Loop through all users in the league
    for user_id, user_name in league_users.items():
        balance = user_balances.get(user_id, initial_balance)

        logging.debug(f"User: {user_name}; Starter balance: {balance}")

        user_stats = leagues.user_stats(user_token, selected_league.id, user_id)
        team_value = user_stats["tv"]
        logging.debug(f"Team value of {user_name}: {team_value}")

        ### Check every item in the all_transfers list if it belongs to the current user
        for item in all_transfers:
            ### Check if item is a buy or sell transfer
            if item["t"] == 15:
                transfer_amount = item["data"]["trp"]

                if "byr" in item["data"] and {value: key for key, value in league_users.items()}.get(item["data"]["byr"]) == user_id:
                    ### User bought a player
                    balance -= transfer_amount

                    player_last_name = item["data"]["pn"]
                    logging.debug(f"{user_name} bought {player_last_name} for {transfer_amount}€")
                    logging.debug(f"New balance: {balance}")
                elif "slr" in item["data"] and {value: key for key, value in league_users.items()}.get(item["data"]["slr"]) == user_id:
                    ### User sold a player
                    balance += transfer_amount

                    player_last_name = item["data"]["pn"]
                    logging.debug(f"{user_name} sold {player_last_name} for {transfer_amount}€")
                    logging.debug(f"New balance: {balance}")

        ### Update the user balance
        user_balances[user_id] = balance

        ### Calculate the adjusted team value
        adjusted_team_value = team_value + balance

        ### Calculate the maximum allowable negative balance
        max_negative_balance = adjusted_team_value * 0.33

        ### Calculate the maxbid
        if balance < 0:
            maxbid = max_negative_balance + balance
        else:
            maxbid = max_negative_balance

        ### Ensure maxbid is not negative
        maxbid = max(0, maxbid)

        ### Create a custom json dict for every user
        final_balances.append({
            "userId": user_id,
            "username": user_name,
            "profilePic": miscellaneous.get_profilepic(user_id),
            "teamValue": team_value,
            "balance": round(balance, 0),
            "maxBid": round(maxbid, 0),
        })

    logging.info("Got balances.")

    ### Save to file + timestamp
    miscellaneous.write_json_to_file(final_balances, "balances.json")
    miscellaneous.write_json_to_file({"time": datetime.now().isoformat()}, "ts_balances.json")

### -------------------------------------------------------------------
### -------------------------------------------------------------------
### -------------------------------------------------------------------

if __name__ == "__main__":
    ### Try to get the logins and Discord URL from the environment variables (Docker)
    kb_mail = getenv("KB_MAIL")
    kb_password = getenv("KB_PASSWORD")
    discord_webhook = getenv("DISCORD_WEBHOOK")

    ### -------------------------------------------------------------------

    tprint("\n\nKB-Insights")
    print("\x1B[3mby casudo\x1B[0m")
    print(f"\x1B[3m{__version__}\x1B[0m\n\n")    

    start_time = time.time()

    main()

    ### Timestamp for frontend
    miscellaneous.write_json_to_file({"time": datetime.now().isoformat()}, "ts_main.json")

    elapsed_time_seconds = time.time() - start_time
    minutes = int(elapsed_time_seconds // 60)
    seconds = int(elapsed_time_seconds % 60)
    logging.info(f"DONE! Execution time: {minutes}m {seconds}s")