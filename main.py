import json
import time
import logging

from os import getenv, makedirs, path, getcwd
from art import tprint
from sys import stdout
from logging.config import dictConfig
from datetime import datetime, timedelta

from backend import exceptions, miscellaneous
# from backend.kickbase.v1 import user, leagues as leagues_v1, competition as competition_v1
# from backend.kickbase.v2 import leagues as leagues_v2
# from backend.kickbase.v3 import competition as competition_v3
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
        league_list, selected_league, user_token = login()

        ### Get the daily login gift in every available league
        get_gift(user_token, league_list)

        market(user_token, selected_league)
        market_value_changes(user_token, selected_league)

        # league_users = taken_free_players_v1(user_token, selected_league)
        league_users = taken_free_players_v2(user_token, selected_league)

        balances(user_token, selected_league, league_users)

        # turnovers_v1(user_token, selected_league, league_users)
        turnovers_v2(user_token, selected_league, league_users)

        team_value_per_match_day(user_token, selected_league, league_users)
        league_user_stats_tables(user_token, selected_league, league_users)
        live_points(user_token, selected_league) # needs to be run first to initialize the live_points.json file

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
            -- league_list (list): List of leagues the user is in.
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

    return league_list, selected_league, user_token


def get_gift(user_token: str, league_list: list) -> None:
    """### Collect the daily login gift in every available league.

    Args:
        user_token (str): The user's kkstrauth token.
        league_list (list): List of leagues the user is in.
    """
    for league in league_list:
        gift = leagues_v1.is_gift_available(user_token, league.id)

        ### Check if dict in gift has {'isAvailable': True}:
        if gift["isAvailable"]:
            logging.info(f"Gift available in league {league.name}!")
            miscellaneous.discord_notification("Kickbase Gift available!", f"Amount: {gift['amount']}\nLevel: {gift['level']}", 6617600, discord_webhook) # TODO: Change color
            leagues_v1.get_gift(user_token, league.id) # TODO: Try, except needed here?, TODO: Check response
        else:
            logging.info(f"Gift has already been collected in league '{league.name}'!")
            # miscellaneous.discord_notification("Kickbase Gift not available!", f"Gift not available!", 6617600, discord_webhook) # TODO: Change color


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
                "twoDaysAgo": player_marketvalue[-3]["mv"] - player_marketvalue[-4]["mv"],
                "sevenDaysAvg": player_marketvalue[-1]["mv"] - player_marketvalue[-8]["mv"] if len(player_marketvalue) >= 8 else None,
                "thirtyDaysAvg": player_marketvalue[-1]["mv"] - player_marketvalue[-31]["mv"] if len(player_marketvalue) >= 31 else None,
                "manager": manager,
            })
            logging.debug(f"Player {player_stats.get('fn', None)} {player_stats['ln']} has a market value of {player_stats['mv']} and is owned by {manager}.")

    logging.info("Got all market value changes for all players.")

    ### Save to file + timestamp
    miscellaneous.write_json_to_file(players_LIST, "market_value_changes.json")
    miscellaneous.write_json_to_file({"time": datetime.now().isoformat()}, "ts_market_value_changes.json")


def taken_free_players_v1(user_token: str, selected_league: object) -> dict:
    """### Retrieves all taken and free players in the league.

    Args:
        user_token (str): The user's kkstrauth token.
        selected_league (object): The league the user wants to get data from for the frontend.

    Returns:
        dict: A dictionary containing all users in the league.
    """
    ### To get the taken players, we first cycle through the individual users BUY/SELL feed to determine which players are bought by the user.
    ### In case a player was assigned to the user on league join, the player is not in the BUY/SELL feed.
    ### To indicate these players, we cycle through ALL players of a team and check if the player is owned by a user.

    logging.info("Getting taken players...")

    ### We start by cycling through the users BUY/SELL feed. The players will be stored in the below list.
    user_transfers_result = []

    ### After that, we check the teams for starter players.
    team_players_result = []

    ### The final results of both lists will be combined into the final_result list below.
    final_result = []

    ### Get all users in the league
    league_users = leagues_v1.league_users(user_token, selected_league.id)
    logging.debug(f"DEBUG of USERS: {league_users['users'][0]}")

    ### Loop through all users in the league
    for real_user in league_users.get("users"):
        logging.debug(f"Username: {real_user['name']}")
        logging.debug(f"Real user id: {real_user['id']}")

        taken_players = []
        user_has_sold = set()

        ### Get all transfers of a user
        user_transfers = leagues_v1.user_transfers(user_token, selected_league.id, real_user["id"])
        logging.debug(f"Found {len(user_transfers)} transfers for user {real_user['name']}")

        ### Loop through all transfers of a user (done by getting the user specific BUY/SELL feed)
        for transfer in user_transfers:
            ### Search the stats of the given player ID to fill the missing attributes for the player which cannot be found in the BUY/SELL feed
            player_stats = leagues_v1.player_statistics(user_token, selected_league.id, transfer["meta"]["pid"])
            logging.debug(f"Player stats: {player_stats['position']}")

            ### If player wasn't bought OR player ID is in the list of players the user has sold
            ### Since the BUY/SELL feed of a user contains ALL transfers, a player could be listed multiple times (bought, sold, bought, sold and so on).
            ### To prevent the player from being added to the list of taken players, we check if the player was NOT bought and ISNT in the sold list.
            ### Now when the scripts runs through the BUY/SELL feed (newest to oldest), there are 3 possible cases:
            ###     1. Player was bought => Add player to the list of taken players
            ###     2. Player was sold => Add player to sold list
            ###     3. Player was bought but sold in an earlier event => Add player to sold list
            if transfer["type"] != 12 or transfer["meta"]["pid"] in user_has_sold:
                ### Add player ID to the dict of players the user has sold
                user_has_sold.add(transfer["meta"]["pid"])
                ### Skip to next player
                continue
            
            ### Check if position number is valid
            position_nr = player_stats["position"]
            if position_nr not in miscellaneous.POSITIONS:
                logging.warning(f"Invalid position number: {position_nr} for player {player_stats['firstName']} {player_stats['lastName']} (PID: {player_stats['id']})")
                position_nr = 1 ### Default to "Torwart" (Goalkeeper)

            ### Create a custom json dict for every player. This will be passed to the frontend later.
            taken_players.append({
                "playerId": transfer["meta"]["pid"],
                "user": real_user["name"],
                "teamId": player_stats["teamId"],
                "position": miscellaneous.POSITIONS[position_nr],
                "firstName": transfer["meta"]["pfn"],
                "lastName": transfer["meta"]["pln"],
                "buyPrice": transfer["meta"]["p"],
                "marketValue": player_stats["marketValue"],
                "status": player_stats["status"],
                "trend": player_stats["mvTrend"],
            })

        ### For every user in the league, add the taken players list to the user_transfers_result list
        user_transfers_result += taken_players

    ### Cycle through all players of a team and check if the player is owned by a user
    ### It could be the case that a player was assigned to a user on league join, therefore the player is not in the BUY/SELL feed
    starter_players = []

    ### Cycle through all teams
    for team_id in miscellaneous.get_team_ids(user_token):
        ### Cycle through all players of the team
        for player in competition_v1.team_players(user_token, team_id):
            ### Search the stats of the given player ID to fill the missing attributes for the player which cannot be found from the team_players endpoint
            player_stats = leagues_v1.player_statistics(user_token, selected_league.id, player.id)

            ### If the player Id is NOT SOMEWHERE in the list of taken players (user_transfers_result) AND the player has a username attribute (is owned by a user)
            if not any(player.id == p.get("playerId") for p in user_transfers_result) and player_stats.get("userName") is not None:
                logging.debug(f"Player {player.firstName} {player.lastName} isn't on the list of taken players, but is owned by user {player_stats.get('userName')}!")

                ### Check if position number is valid
                if player.position not in miscellaneous.POSITIONS:
                    logging.warning(f"Invalid position number: {player.position} for player {player.firstName} {player.lastName} (PID: {player.id})")
                    player.position = 1 ### Default to "Torwart" (Goalkeeper)

                ### Create a custom json dict for every starter player. This will be passed to the frontend later.
                starter_players.append({
                    "playerId": player.id,
                    "user": player_stats["userName"],
                    "teamId": player.teamId,
                    "position": miscellaneous.POSITIONS[player.position],
                    "firstName": player.firstName,
                    "lastName": player.lastName,
                    "buyPrice": 0,
                    "marketValue": player.marketValue,
                    "status": player.status,
                    "trend": player.marketValueTrend,
                })

    ### Now we add the list of both checks to the final_result list.
    team_players_result += starter_players
    final_result = (user_transfers_result + team_players_result) 

    logging.info("Got all taken players.")
    
    ### Save to file + timestamp
    miscellaneous.write_json_to_file(final_result, "taken_players.json")
    miscellaneous.write_json_to_file({"time": datetime.now().isoformat()}, "ts_taken_players.json")

    ### Based on all taken players, we can now get all free players
    miscellaneous.get_free_players(user_token, final_result)

    return league_users


def taken_free_players_v2(user_token: str, selected_league: object) -> dict:
    """### Retrieves all taken and free players in the league.

    Args:
        user_token (str): The user's kkstrauth token.
        selected_league (object): The league the user wants to get data from for the frontend.

    Returns:
        dict: A dictionary containing all users in the league.
    """
    logging.info("Getting taken and free players...")

    taken_players = []
    free_players = []

    ### Get all users in the league
    league_users = leagues_v1.league_users(user_token, selected_league.id)
    logging.debug(f"DEBUG of USERS: {league_users['users'][0]}")

    ### Create a set of user IDs for quick lookup
    user_ids = {user["id"]: user["name"] for user in league_users.get("users")}

    ### Get all transfers in the league
    all_transfers = leagues_v2.transfers(user_token, selected_league.id)

    ### Create a dictionary to store buy prices from transfers
    buy_prices = {}
    for transfer in all_transfers:
        if "b" in transfer["meta"]:
            user_id = transfer["meta"]["b"]["i"]
            player_id = transfer["meta"]["p"]["i"]
            buy_price = transfer["meta"]["v"]

            if user_id not in buy_prices:
                buy_prices[user_id] = []
            
            buy_prices[user_id].append((player_id, buy_price))

    ### Cycle through all teams
    for team_id in miscellaneous.get_team_ids(user_token):
        ### Cycle through all players of the team
        for player in competition_v1.team_players(user_token, team_id):
            ### Search the stats of the given player ID to fill the missing attributes for the player
            player_stats = leagues_v1.player_statistics(user_token, selected_league.id, player.id)

            ### Check if the player is owned by a user
            if player_stats.get("userName") in user_ids.values():
                logging.debug(f"Player {player.firstName} {player.lastName} is owned by user {player_stats.get('userName')}!")

                ### Check if position number is valid
                if player.position not in miscellaneous.POSITIONS:
                    logging.warning(f"Invalid position number: {player.position} for player {player.firstName} {player.lastName} (PID: {player.id})")
                    player.position = 1 ### Default to "Torwart" (Goalkeeper)

                ### Determine the buy price
                current_user_id = player_stats["userId"]
                buy_price = 0
                if current_user_id in buy_prices:
                    for pid, price in buy_prices[current_user_id]:
                        if pid == player.id:
                            buy_price = price
                            break

                if buy_price == 0:
                    ### Set the buyPrice to the "m" value in the "marketValues" list where "day" is the START_DATE
                    ### Loop through all marketValues of the player until the "day" matches the START_DATE
                    start_date = datetime.strptime(getenv("START_DATE"), "%d.%m.%Y").date()

                    for marketValue in player_stats["marketValues"]:
                        ### Normalize the marketValue date to date only
                        market_value_date = datetime.fromisoformat(marketValue["d"].replace("Z", "")).date()

                        if market_value_date == start_date:
                            buy_price = marketValue["m"]
                            logging.debug(f"Player {player.firstName} {player.lastName} was assigned at the start of the season. Market value on START_DATE {start_date}: {buy_price}€.")
                            break

                ### Create a custom json dict for every taken player. This will be passed to the frontend later.
                taken_players.append({
                    "owner": player_stats["userName"],
                    "playerId": player.id,
                    "teamId": player.teamId,
                    "position": miscellaneous.POSITIONS[player.position],
                    "firstName": player.firstName,
                    "lastName": player.lastName,
                    "buyPrice": buy_price,
                    "marketValue": player.marketValue,
                    "status": player.status,
                    "trend": player.marketValueTrend,
                })
            else:
                ### Create a custom json dict for every free player. This will be passed to the frontend later.
                free_players.append({
                    "playerId": player.id,
                    "teamId": player.teamId,
                    "position": miscellaneous.POSITIONS[player.position],
                    "firstName": player.firstName,
                    "lastName": player.lastName,
                    "marketValue": player.marketValue,
                    "points": player.totalPoints,
                    "status": player.status,
                    "trend": player.marketValueTrend,
                })

    logging.info("Got all taken and free players.")
    
    ### Save to file + timestamp
    miscellaneous.write_json_to_file(taken_players, "taken_players.json")
    miscellaneous.write_json_to_file({"time": datetime.now().isoformat()}, "ts_taken_players.json")

    ### Save to file + timestamp
    miscellaneous.write_json_to_file(free_players, "free_players.json")
    miscellaneous.write_json_to_file({"time": datetime.now().isoformat()}, "ts_free_players.json")

    return league_users


def turnovers_v1(user_token: str, selected_league: object, league_users: dict) -> None:
    """### Retrieves all turnovers in the league.

    Args:
        user_token (str): The user's kkstrauth token.
        selected_league (object): The league the user wants to get data from for the frontend.
        league_users (dict): A dictionary containing all users in the league.
    """
    logging.info("Getting turnovers...")

    final_turnovers = []

    ### Loop through all users in the league
    for real_user in league_users.get("users"):
        logging.debug(f"Username: {real_user['name']}")
        logging.debug(f"Real user id: {real_user['id']}")

        transfers = []
        
        ### Get all transfers of a user
        user_transfers = leagues_v1.user_transfers(user_token, selected_league.id, real_user["id"])
        logging.debug(f"Found {len(user_transfers)} transfers for user {real_user['name']}")

        ### Cycle through all transfers of a user
        for buy in user_transfers:
            ### Check if the transfer type is a buy
            transfer_type = "buy" if buy["type"] == 12 else "sell"

            ### Get the trade partner
            if "bn" in buy["meta"]:
                trade_partner = buy["meta"]["bn"]
            elif "sn" in buy["meta"]:
                trade_partner = buy["meta"]["sn"]
            else:
                trade_partner = "Kickbase"

            ### Create a custom json dict for every transfer
            transfers.append({
                "date": buy["date"],
                "type": transfer_type,
                "user": real_user["name"],
                "tradePartner": trade_partner,
                "price": buy["meta"]["p"],
                "playerId": buy["meta"]["pid"],
                "teamId": buy["meta"]["tid"],
                "firstName": f"{buy['meta']['pfn']}", 
                "lastName": f"{buy['meta']['pln']}",
            })  

        ### Removes duplicates given by the API
        transfers = list({frozenset(item.items()): item for item in transfers}.values())
        transfers.reverse() ### Oldest is first.

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

                ### If an unmatched sell transfer is found, a simulated buy transfer is created with some default values
                date = datetime.strptime(getenv("START_DATE"), "%d.%m.%Y").isoformat()
                buy_transfer = {"date": date,
                                "type": "buy",
                                "user": transfer["user"],
                                "tradePartner": "Kickbase",
                                "price": transfer["price"], # "price": 0.0,
                                "playerId": transfer["playerId"],
                                "teamId": transfer["teamId"],
                                "firstName": transfer["firstName"],
                                "lastName": transfer["lastName"]}

                turnovers.append((buy_transfer, transfer))

        final_turnovers += turnovers

    logging.info("Got all turnovers.")

    ### Save to file + timestamp
    miscellaneous.write_json_to_file(final_turnovers, "turnovers.json")
    miscellaneous.write_json_to_file({"time": datetime.now().isoformat()}, "ts_turnovers.json")

    ### Calculate revenue data for the graph
    miscellaneous.calculate_revenue_data_daily(final_turnovers, league_users.get("users"))


def turnovers_v2(user_token: str, selected_league: object, league_users: dict) -> None:
    """### Retrieves all turnovers in the league.

    Args:
        user_token (str): The user's kkstrauth token.
        selected_league (object): The league the user wants to get data from for the frontend.
        league_users (dict): A dictionary containing all users in the league.
    """
    logging.info("Getting turnovers...")

    final_turnovers = []

    ### Load existing transfers from all_transfers.json
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
    new_transfers = leagues_v2.transfers(user_token, selected_league.id)
    logging.debug(f"Found {len(new_transfers)} new transfers from the API")

    ### Append only new transfers (ignoring duplicates)
    new_transfer_ids = {item["id"] for item in all_transfers}  # Set of existing transfer IDs
    for transfer in new_transfers:
        if transfer["id"] not in new_transfer_ids:  # Check if the transfer is new
            all_transfers.append(transfer)
            new_transfer_ids.add(transfer["id"])  # Update the set to include the new transfer

    ### Sort transfers by date after appending new ones
    all_transfers.sort(key=lambda x: datetime.fromisoformat(x["date"].replace("Z", "")))

    logging.debug(f"Total transfers after appending new ones: {len(all_transfers)}")

    ### Save updated transfers back to all_transfers.json
    miscellaneous.write_json_to_file(all_transfers, "all_transfers.json")
    logging.debug("Updated all_transfers.json with new transfers")

    ### Process the transfers as usual
    transfers = []

    ### Process each transfer item
    for item in all_transfers:
        ### Determine the transfer type based on the type and metadata
        if item["type"] == 15:
            if "s" in item["meta"] and "b" in item["meta"]:
                transfer_type = "sell"
                user = item["meta"]["s"]["n"]
                trade_partner = item["meta"]["b"]["n"]
            elif "s" in item["meta"]:
                transfer_type = "sell"
                user = item["meta"]["s"]["n"]
                trade_partner = "Kickbase"
            elif "b" in item["meta"]:
                transfer_type = "buy"
                user = item["meta"]["b"]["n"]
                trade_partner = "Kickbase"
            else:
                transfer_type = "unknown"
        else:
            transfer_type = "unknown"

        ### Search the stats of the given player ID to fill the missing attributes for the player
        player_stats = leagues_v1.player_statistics(user_token, selected_league.id, item["meta"]["p"]["i"])

        ### Create a custom json dict for every transfer
        transfers.append({
            "date": item["date"],
            "type": transfer_type,
            "user": user,
            "tradePartner": trade_partner,
            "price": item["meta"]["v"],
            "playerId": item["meta"]["p"]["i"],
            "teamId": item["meta"]["p"]["t"],
            "firstName": player_stats["firstName"],
            "lastName": player_stats["lastName"],
        })

    ### Removes duplicates given by the API
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

            ### Search the stats of the given player ID to fill the missing attributes for the player
            player_stats = leagues_v1.player_statistics(user_token, selected_league.id, transfer["playerId"])

            ### Loop through all marketValues of the player until the "day" matches the START_DATE
            start_date = datetime.strptime(getenv("START_DATE"), "%d.%m.%Y").date()

            for marketValue in player_stats["marketValues"]:
                ### Normalize the marketValue date to date only
                market_value_date = datetime.fromisoformat(marketValue["d"].replace("Z", "")).date()

                if market_value_date == start_date:
                    price = marketValue["m"]
                    logging.debug(f"Starter player {transfer['firstName']} {transfer['lastName']} was sold! Market value on START_DATE {start_date}: {price}€.")
                    break

            ### If an unmatched sell transfer is found, a simulated buy transfer is created with some default values
            date = datetime.strptime(getenv("START_DATE"), "%d.%m.%Y").isoformat()
            buy_transfer = {"date": date,
                            "type": "assigned_at_start",
                            "user": transfer["user"],
                            "tradePartner": "Kickbase",
                            "price": price,
                            "playerId": transfer["playerId"],
                            "teamId": transfer["teamId"],
                            "firstName": player_stats["firstName"],
                            "lastName": player_stats["lastName"],
                        }

            turnovers.append((buy_transfer, transfer))

    final_turnovers += turnovers

    logging.info("Got all turnovers.")

    ### Save to file + timestamp
    miscellaneous.write_json_to_file(final_turnovers, "turnovers.json")
    miscellaneous.write_json_to_file({"time": datetime.now().isoformat()}, "ts_turnovers.json")

    ### Calculate revenue data for the graph
    miscellaneous.calculate_revenue_data_daily(final_turnovers, league_users.get("users"))


def team_value_per_match_day(user_token: str, selected_league: object, league_users: dict) -> None:
    """### Calculates the team value per match day for all users in the league.

    Args:
        user_token (str): The user's kkstrauth token.
        selected_league (object): The league the user wants to get data from for the frontend.
        league_users (dict): A dictionary containing all users in the league.
    """
    logging.info("Calculating team value per match day...")

    final_team_value = {}

    ### Get all match days of the season
    match_days_list = competition_v3.match_days(user_token)

    ### Get the current match day and team values per match day
    match_day_stats = leagues_v1.league_stats(user_token, selected_league.id)
    
    ### Loop through all users in the league
    for real_user in league_users.get("users"):
        ### Get the current match day from league_stats
        current_match_day = match_day_stats["currentDay"]

        ### Get the team value for each match day
        team_value = {match_day: 0 for match_day in range(1, current_match_day + 1)}
    
        ### Loop through all match days
        for match_day in match_days_list:
            ### Skip processing if the match day is in the future
            if match_day["day"] > current_match_day:
                continue
        
            team_value_on_match_day = 0

            ### Loop through all users of the match day
            for match_day_user in match_day_stats["matchDays"][match_day["day"] - 1]["users"]:
                if match_day_user["userId"] == real_user["id"]:
                    team_value_on_match_day = match_day_user["teamValue"]
                    break
        
            if len(team_value) >= match_day["day"]:
                team_value[match_day["day"]] = team_value_on_match_day
        
        final_team_value[real_user["name"]] = team_value

    logging.info("Calculated team value per match day.")

    ### Save to file + timestamp
    miscellaneous.write_json_to_file(final_team_value, "team_values.json")
    miscellaneous.write_json_to_file({"time": datetime.now().isoformat()}, "ts_team_values.json")


def league_user_stats_tables(user_token: str, selected_league: object, league_users: dict) -> None:
    """### Retrieves the statistics for all users in the league.

    Args:
        user_token (str): The user's kkstrauth token.
        selected_league (object): The league the user wants to get data from for the frontend.
        league_users (dict): A dictionary containing all users in the league.
    """
    logging.info("Getting league user stats...")

    final_user_stats = []

    ### Loop through all users in the league
    for real_user in league_users.get("users"):
        ### Get stats for each user
        user_stats = leagues_v1.user_stats(user_token, selected_league.id, real_user["id"])

        def get_season_stat(user_stats: dict , stat: str, default: int=0) -> int:
            """Safely get a stat from the first season in user_stats.
            That's because if the user hasn't interacted in the new season yet, the seasons list is empty.
            """
            seasons = user_stats.get("seasons", [])
            if seasons:
                return seasons[0].get(stat, default) # seasons[0] is the current season
            return default

        ### Create a custom json dict for every user
        final_user_stats.append({
            ### Shared stats 
            "userId": real_user["id"],
            "userName": real_user["name"],
            "profilePic": user_stats.get("profileUrl", None),
            "mdWins": get_season_stat(user_stats, "wins"),
            "maxPoints": get_season_stat(user_stats, "maxPoints"),
            ### Stats for "Liga -> Tabelle" ONLY
            "placement": user_stats["placement"],
            "points": user_stats["points"],
            "teamValue": user_stats["teamValue"],
            # "maxBuyPrice": user_stats["leagueUser"]["maxBuyPrice"],
            # "maxBuyFirstName": user_stats["leagueUser"]["maxBuyFirstName"],
            # "maxBuyLastName": user_stats["leagueUser"]["maxBuyLastName"],
            # "maxSellPrice": user_stats["leagueUser"]["maxSellPrice"],
            # "maxSellFirstName": user_stats["leagueUser"]["maxSellFirstName"],
            # "maxSellLastName": user_stats["leagueUser"]["maxSellLastName"]
            ### Stats for "Liga -> Saison Statistiken" ONLY
            "avgPoints": get_season_stat(user_stats, "averagePoints"),
            "minPoints": get_season_stat(user_stats, "minPoints"),
            "bought": get_season_stat(user_stats, "bought"),
            "sold": get_season_stat(user_stats, "sold"),
            ### Stats for "Liga -> Battles" ONLY
            "pointsGoalKeeper": get_season_stat(user_stats, "pointsGoalKeeper"),
            "pointsDefenders": get_season_stat(user_stats, "pointsDefenders"),
            "pointsMidFielders": get_season_stat(user_stats, "pointsMidFielders"),
            "pointsForwards": get_season_stat(user_stats, "pointsForwards"),
            "combinedTransfers": get_season_stat(user_stats, "bought", 0) + get_season_stat(user_stats, "sold", 0),
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


def balances(user_token: str, selected_league: object, league_users: dict) -> None:
    """### Retrieves the estiamted balances for all users in the league. Daily login bonus and money from achievements are not considered.

    Args:
        user_token (str): The user's kkstrauth token.
        selected_league (object): The league the user wants to get data from for the frontend.
        league_users (dict): A dictionary containing all users in the league.

    Returns:
        None
    """
    logging.info("Getting balances...")

    initial_balance = float(getenv("START_MONEY", 50000000))
    final_balances = []

    ### Get all transfers from the API
    all_transfers = leagues_v2.transfers(user_token, selected_league.id)
    logging.debug(f"Found {len(all_transfers)} transfers in total")

    ### Initialize user balances
    user_balances = {user["id"]: initial_balance for user in league_users.get("users")}

    ### Loop through all users in the league
    for real_user in league_users.get("users"):
        user_id = real_user["id"]
        balance = user_balances.get(user_id, initial_balance)

        logging.debug(f"User: {real_user['name']}")
        logging.debug(f"Starter balance: {balance}")

        user_stats = leagues_v1.user_stats(user_token, selected_league.id, real_user["id"])
        team_value = user_stats["teamValue"]

        logging.debug(f"Team value: {team_value}")

        ### Check every item in the all_transfers list if it belongs to the current user
        for item in all_transfers:
            meta = item["meta"]
            transfer_amount = meta.get("v")

            if "b" in meta and meta["b"]["i"] == user_id:
                ### User bought a player
                balance -= transfer_amount

                player_name = meta["p"]["n"]
                logging.debug(f"{real_user['name']} bought {player_name} for {transfer_amount}€")
                logging.debug(f"New balance: {balance}")
            elif "s" in meta and meta["s"]["i"] == user_id:
                ### User sold a player
                balance += transfer_amount

                player_name = meta["p"]["n"]
                logging.debug(f"{real_user['name']} sold {player_name} for {transfer_amount}€")
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
            "username": real_user["name"],
            "profilePic": user_stats.get("profileUrl", None),
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