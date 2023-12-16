import json, time, argparse, logging
from logging.config import dictConfig
from datetime import datetime, timedelta
from os import getenv
from art import tprint
from sys import stdout

from kickbase import exceptions, user, miscellaneous, leagues, competition

### -------------------------------------------------------------------
### -------------------------------------------------------------------
### -------------------------------------------------------------------


def main():
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
                "filename": "/code/logs/kickbase-insights.log",
                "when": "D",
                "interval": 30, # overwrite interval in days
                "backupCount": 0, # don't keep any backups
                "formatter": "simple",
            },
            "verbose_file": { # Log EVERYTHING to file (verbose format)
                "level": "DEBUG",
                "class": "logging.handlers.TimedRotatingFileHandler",
                "filename": "/code/logs/kickbase-insights-verbose.log",
                "when": "D",
                "interval": 14, # overwrite interval in days
                "backupCount": 0, # don't keep any backups
                "formatter": "verbose",
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
        user_info, league_info, user_token = login()
        gift(user_token, league_info)

        league_user_info = leagues.league_user_info(user_token, league_info[0].id)
        logging.debug(f"=== Statistics for {user_info.name} in league {league_info[0].name} ===")
        logging.debug(f"Budget: {league_user_info.budget}€")
        logging.debug(f"Team value: {league_user_info.teamValue}€")
        logging.debug(f"Points: {league_user_info.points}")
        logging.debug(f"Rank: {league_user_info.placement}")

        league_feed(user_token, league_info)
        market(user_token, league_info)
        market_value_changes(user_token, league_info)
        league_users = taken_free_players(user_token, league_info)
        turnovers(user_token, league_info, league_users)
        team_value_per_match_day(user_token, league_info, league_users)
        league_user_stats_tables(user_token, league_info, league_users)
        live_points(user_token, league_info) # needs to be run first to initialize the live_points.json file

    except exceptions.LoginException as e:
        print(e)
        return
    except exceptions.NotificatonException as e:
        print(e)
        return
    except exceptions.KickbaseException as e:
        print(e)
        return
    

def login():
    logging.info("Logging in...")

    ### If script is executed locally, use the arguments from the command line
    if args.usermail and args.password:
        user_info, league_info, user_token = user.login(args.usermail, args.password)
    ### else when script is executed in Docker, use the environment variables
    else:
        user_info, league_info, user_token = user.login(kb_mail, kb_password)

    ### TODO: Format?
    logging.debug(f"{user_info.name}")
    logging.debug(f"{league_info[0].name}")
    logging.debug(f"{league_info[0].pub}")
    logging.debug(f"{user_token}")

    logging.info(f"Successfully logged in as {user_info.name}\n")
    logging.info(f"Available leagues: {', '.join([league.name for league in league_info])}") # Print all available leagues the user is in

    return user_info, league_info, user_token


def gift(user_token, league_info):
    gift = leagues.is_gift_available(user_token, league_info[0].id)

    ### Check if dict in gift has {'isAvailable': True}:
    if gift["isAvailable"]:
        logging.info(f"Gift available in league {league_info[0].name}!\n")
        miscellaneous.discord_notification("Kickbase Gift available!", f"Amount: {gift['amount']}\nLevel: {gift['level']}", 6617600, args.discord if args.discord else discord_webhook) # TODO: Change color
        leagues.get_gift(user_token, league_info[0].id) # TODO: Try, except needed here?, TODO: Check response
    else:
        logging.info(f"Gift has already been collected in league {league_info[0].name}!\n")
        # miscellaneous.discord_notification("Kickbase Gift not available!", f"Gift not available!", 6617600, args.discord if args.discord else discord_webhook) # TODO: Change color   


def league_feed(user_token, league_info):
    ### Get the 30 latest feed entries
    league_feed = leagues.league_feed(user_token, league_info[0].id)
    ### Loop through the feed entries and print them
    logging.info(f"{league_info[0].name}'s feed (latest 30):")
    print("=====FEED START=====")
    for feed_entry in league_feed:
        print("------------------------")
        print(f"| {feed_entry.meta.pfn} {feed_entry.meta.pln}") # | Manuel Neuer

        ### Type 2: User sold to Kickbase AND User sold to User
        if feed_entry.type == 2 and not feed_entry.meta.bn: # Type 2 = User sold to Kickbase
            formatted_price = '{:,.0f}'.format(feed_entry.meta.p).replace(',', '.') # 5.000.561 instead of 5000561.0
            print(f"| Sold from {feed_entry.meta.sn} to Kickbase for {formatted_price}€") # | Sold from USER to Kickbase for 5.000.561€
        elif feed_entry.type == 2 and feed_entry.meta.bn: # Type 2 = User sold to User
            formatted_price = '{:,.0f}'.format(feed_entry.meta.p).replace(',', '.') # 5.000.561 instead of 5000561.0
            print(f"| Sold from {feed_entry.meta.sn} to {feed_entry.meta.bn} for {formatted_price}€") # | Sold from USER to USER for 5.000.561€
        
        ### Type 3: Listed by Kickbase
        if feed_entry.type == 3: 
            raw_age = feed_entry.age

            ### Calculate days, hours, and minutes
            days, remainder = divmod(raw_age, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, _ = divmod(remainder, 60)

            ### Create a formatted string based on the calculated values
            formatted_age = ""
            if days > 0:
                formatted_age += f"{days}d "
            if hours > 0:
                formatted_age += f"{hours}h "
            if minutes > 0 or (days == 0 and hours == 0):  # Show minutes if no days or hours
                formatted_age += f"{minutes}m"

            print(f"| Listed since: {formatted_age}")

        ### TODO: Add type 8 (final matchday points)

        ### Type 12: User bought from Kickbase
        if feed_entry.type == 12: 
            formatted_price = '{:,.0f}'.format(feed_entry.meta.p).replace(',', '.') # 5.000.561 instead of 5000561.0
            print(f"| Sold from Kickbase to {feed_entry.meta.bn} for {formatted_price}€") # | Sold from Kickbase to USER for 5.000.561€
    print("=====FEED END=====\n")    


def market(user_token, league_info):
    logging.info("Getting players listed on transfer market...")

    ### Get all players on the market
    players_on_market = leagues.get_market(user_token, league_info[0].id)

    players_listed_by_user = []
    players_listed_by_kickbase = []

    for player in players_on_market:
        ### Check if player is listed by user
        if not player.username:
            ### Create a custom json dict for every player listed by real users
            players_listed_by_kickbase.append({
                "teamId": player.teamId,
                "position": miscellaneous.POSITIONS[player.position],
                "firstName": f"{player.firstName}", 
                "lastName": f"{player.lastName}",
                "price": player.price,
                "status": player.status,
                "trend": player.marketValueTrend,
                "expiration": (datetime.now() + timedelta(seconds=player.expiry)).strftime('%d.%m.%Y %H:%M:%S'),
            })
            logging.debug(f"Player {player.firstName} {player.lastName} is listed by Kickbase!")
        else:
            ### Create a custom json dict for every player listed by kickbase
            players_listed_by_user.append({
                "teamId": player.teamId,
                "position": miscellaneous.POSITIONS[player.position],
                "firstName": f"{player.firstName}", 
                "lastName": f"{player.lastName}",
                "price": player.price,
                "status": player.status,
                "trend": player.marketValueTrend,
                "seller": player.username,
                "expiration": (datetime.now() + timedelta(seconds=player.expiry)).strftime('%d.%m.%Y %H:%M:%S'),
            }) ### TODO: Fix expiration TZ
            logging.debug(f"Player {player.firstName} {player.lastName} is listed by {player.username}!")

    logging.info("Got all players listed on transfer market.\n")

    ### Write the json dicts to a file. These will be read by the frontend.
    with open("/code/frontend/src/data/market_user.json", "w") as f:
        f.write(json.dumps(players_listed_by_user, indent=2))
        logging.debug("Created file market_user.json")
    with open("/code/frontend/src/data/market_kickbase.json", "w") as f:
        f.write(json.dumps(players_listed_by_kickbase, indent=2))
        logging.debug("Created file market_kickbase.json")

    ### Timestamp for frontend
    with open("/code/frontend/src/data/timestamps/ts_market_user.json", "w") as f:
        f.writelines(json.dumps({'time': datetime.now(tz=miscellaneous.TIMEZONE_DE).isoformat()}))
        logging.debug("Created file ts_market_user.json")
    with open("/code/frontend/src/data/timestamps/ts_market_kickbase.json", "w") as f:
        f.writelines(json.dumps({'time': datetime.now(tz=miscellaneous.TIMEZONE_DE).isoformat()}))
        logging.debug("Created file ts_market_kickbase.json")


def market_value_changes(user_token, league_info):
    logging.info("Getting market value changes for all players...")

    players_LIST = []

    ### Loop through all teams
    for team in miscellaneous.TEAM_IDS:
        ### Loop through all players in the team
        for player in competition.team_players(user_token, team):
            ### Get the market value changes for the player
            player_stats = leagues.player_statistics(user_token, league_info[0].id, player.p.id)

            ### Check if player is owned by user
            if "leaguePlayer" in player_stats:
                manager = player_stats["leaguePlayer"]["userName"]
            else:
                manager = "Kickbase"

            ### Create a custom json dict for every player
            players_LIST.append({
                "teamId": player_stats["teamId"],
                "position": miscellaneous.POSITIONS[player_stats["position"]],
                "firstName": player_stats["firstName"], # "firstName": f"{player.p.firstName}", 
                "lastName": player_stats["lastName"], # "lastName": f"{player.p.lastName}",
                "marketValue": player_stats["marketValue"], # "marketValue": player.p.marketValue,
                "today": (player_stats["marketValue"] - player_stats["marketValues"][-2]["m"]), # "today": (player.p.marketValue - player_stats[-2].m),
                "yesterday": (player_stats["marketValues"][-2]["m"] - player_stats["marketValues"][-3]["m"]),
                "twoDays": (player_stats["marketValues"][-3]["m"] - player_stats["marketValues"][-4]["m"]),
                "SevenDaysAvg": (player_stats["marketValue"] - player_stats["marketValues"][-8]["m"]),
                "ThirtyDaysAvg": (player_stats["marketValue"] - player_stats["marketValues"][-31]["m"]),
                "manager": manager,
            })
            ### TODO: DEBUG print the player

    logging.info("Got all market value changes for all players.\n")

    ### Write the json dicts to a file. These will be read by the frontend.
    with open("/code/frontend/src/data/market_value_changes.json", "w") as f:
        f.write(json.dumps(players_LIST, indent=2))
        logging.debug("Created file market_value_changes.json")

    ### Timestamp for frontend
    with open("/code/frontend/src/data/timestamps/ts_market_value_changes.json", "w") as f:
        f.writelines(json.dumps({'time': datetime.now(tz=miscellaneous.TIMEZONE_DE).isoformat()}))
        logging.debug("Created file ts_market_value_changes.json")


def taken_free_players(user_token, league_info):
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
    league_users = leagues.league_users(user_token, league_info[0].id)
    logging.debug(f"DEBUG of USERS: {league_users['users'][0]}")

    ### Loop through all users in the league
    for real_user in league_users.get("users"):
        logging.debug(f"Username: {real_user['name']}")
        logging.debug(f"Real user id: {real_user['id']}")

        taken_players = []
        user_has_sold = set()

        ### Get all transfers of a user
        user_transfers = leagues.user_players(user_token, league_info[0].id, real_user["id"])
        logging.debug(f"Found {len(user_transfers)} transfers for user {real_user['name']}")

        ### Loop through all transfers of a user (done by getting the user specific BUY/SELL feed)
        for transfer in user_transfers:
            ### Search the stats of the given player ID to fill the missing attributes for the player which cannot be found in the BUY/SELL feed
            player_stats = leagues.player_statistics(user_token, league_info[0].id, transfer["meta"]["pid"])
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
            
            ### Create a custom json dict for every player. This will be passed to the frontend later.
            taken_players.append({
                "playerId": transfer["meta"]["pid"],
                "user": real_user["name"],
                "teamId": player_stats["teamId"],
                "position": miscellaneous.POSITIONS[player_stats["position"]],
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
    for team_id in miscellaneous.TEAM_IDS:
        ### Cycle through all players of the team
        for player in competition.team_players(user_token, team_id):
            player_id = player.p.id
            # print(player_id)

            ### Search the stats of the given player ID to fill the missing attributes for the player which cannot be found from the team_players endpoint
            player_stats = leagues.player_statistics(user_token, league_info[0].id, player.p.id)

            ### If the player Id is NOT SOMEWHERE in the list of taken players (user_transfers_result) AND the player has a username attribute (is owned by a user)
            if not any(player_id == player.get("playerId") for player in user_transfers_result) and player_stats.get("userName") is not None:
                logging.debug(f"Player {player.p.firstName} {player.p.lastName} isn't on the list of taken players, but is owned by user {player_stats.get('userName')}!")

                ### Create a custom json dict for every starter player. This will be passed to the frontend later.
                starter_players.append({
                    "playerId": player_id,
                    "user": player_stats["userName"],
                    "teamId": player.p.teamId,
                    "position": miscellaneous.POSITIONS[player.p.position],
                    "firstName": player.p.firstName,
                    "lastName": player.p.lastName,
                    "buyPrice": 0,
                    "marketValue": player_stats["marketValue"],
                    "status": player_stats["status"],
                    "trend": player_stats["mvTrend"],
                })

    ### Now we add the list of both checks to the final_result list.
    team_players_result += starter_players
    final_result = (user_transfers_result + team_players_result) 

    logging.info("Got all taken players.\n")
    
    ### Write the json dicts to a file. These will be read by the frontend.
    with open("/code/frontend/src/data/taken_players.json", "w") as f:
        f.write(json.dumps(final_result, indent=2))
        logging.debug("Created file taken_players.json")

    ### Timestamp for frontend
    with open("/code/frontend/src/data/timestamps/ts_taken_players.json", "w") as f:
        f.writelines(json.dumps({'time': datetime.now(tz=miscellaneous.TIMEZONE_DE).isoformat()}))
        logging.debug("Created file ts_taken_players.json")

    ### Based on all taken players, we can now get all free players
    miscellaneous.get_free_players(user_token, league_info[0].id, final_result)

    return league_users


def turnovers(user_token, league_info, league_users):
    logging.info("Getting turnovers...")

    final_turnovers = []

    ### Loop through all users in the league
    for real_user in league_users.get("users"):
        logging.debug(f"Username: {real_user['name']}")
        logging.debug(f"Real user id: {real_user['id']}")

        transfers = []
        
        ### Get all transfers of a user
        user_transfers = leagues.user_players(user_token, league_info[0].id, real_user["id"])
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
                if sell_transfer['type'] == 'buy':
                    continue   

                ### This condition checks if the player ID of the current sell transfer matches the player ID of the current buy transfer. 
                ### If there is a match, it means a corresponding buy-sell pair is found.
                if sell_transfer['playerId'] == buy_transfer['playerId']:
                    turnovers.append((buy_transfer, sell_transfer))
                    break

        ### Revenue generated by randomly assigned players
        for transfer in transfers:
            ### Skip buy transfers
            if transfer['type'] == 'buy':
                continue

            ### This condition checks if the current sell transfer is not already part of a buy-sell pair in the turnovers list.
            if transfer not in [turnover[1] for turnover in turnovers]:

                ### If an unmatched sell transfer is found, a simulated buy transfer is created with some default values
                date = datetime(2023, 8, 22).isoformat() ### TODO: Change Startday at the end of the season ???
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

    logging.info("Got all turnovers.\n")

    with open("/code/frontend/src/data/turnovers.json", "w") as f:
        f.write(json.dumps(final_turnovers, indent=2))
        logging.debug("Created file turnovers.json")
    
    ### Timestamp for frontend
    with open("/code/frontend/src/data/timestamps/ts_turnovers.json", "w") as f:
        f.writelines(json.dumps({'time': datetime.now(tz=miscellaneous.TIMEZONE_DE).isoformat()}))
        logging.debug("Created file ts_turnovers.json")

    ### Calculate revenue data for the graph
    miscellaneous.calculate_revenue_data_daily(final_turnovers, league_users.get("users"))


def team_value_per_match_day(user_token, league_info, league_users):
    logging.info("Calculating team value per match day...")

    final_team_value = {}

    ### Loop through all users in the league
    for real_user in league_users.get("users"):
        ### Get last (current) match day
        last_match_day = leagues.league_stats(user_token, league_info[0].id)["currentDay"]

        ### Get team value for each match day
        team_value = {match_day: 0 for match_day in range(1, last_match_day + 1)}
        for match_day in miscellaneous.MATCH_DAYS:

            ### TODO: Reverse userstats["teamValues"] since the below for loop iterates from newest to oldest
            user_stats = leagues.user_stats(user_token, league_info[0].id, real_user["id"])

            team_value_on_match_day = 0
            ### Loop through all team values (per day) of the user
            for teamValues in user_stats["teamValues"]:
                ### Check if the date of the team value matches the date of the match day
                if miscellaneous.MATCH_DAYS[match_day].date() == datetime.fromisoformat(teamValues["d"][:-1]).date():
                    team_value_on_match_day = teamValues["v"]
            
            if (len(team_value) >= match_day):
                team_value[match_day] = team_value_on_match_day

        final_team_value[real_user["name"]] = team_value

    logging.info("Calculated team value per match day.\n")

    with open("/code/frontend/src/data/team_values.json", "w") as f:
        f.write(json.dumps(final_team_value, indent=2))
        logging.debug("Created file team_values.json")

    ### Timestamp for frontend
    with open("/code/frontend/src/data/timestamps/ts_team_values.json", "w") as f:
        f.writelines(json.dumps({'time': datetime.now(tz=miscellaneous.TIMEZONE_DE).isoformat()}))
        logging.debug("Created file ts_team_values.json")


def league_user_stats_tables(user_token, league_info, league_users):
    logging.info("Getting league user stats...")

    final_user_stats = []

    ### Loop through all users in the league
    for real_user in league_users.get("users"):
        ### Get stats for each user
        user_stats = leagues.user_stats(user_token, league_info[0].id, real_user["id"])

        ### Create a custom json dict for every user
        final_user_stats.append({
            ### Shared stats 
            "userId": real_user["id"],
            "userName": real_user["name"],
            "profilePic": user_stats.get("profileUrl", ""),
            "mdWins": user_stats["seasons"][0]["wins"], # for current season
            "maxPoints": user_stats["seasons"][0]["maxPoints"], # for current season
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
            "avgPoints": user_stats["seasons"][0]["averagePoints"], # for current season
            "minPoints": user_stats["seasons"][0]["minPoints"], # for current season
            "bought": user_stats["seasons"][0]["bought"], # for current season
            "sold": user_stats["seasons"][0]["sold"], # for current season
            ### Stats for "Liga -> Battles" ONLY
            "pointsGoalKeeper": user_stats["seasons"][0]["pointsGoalKeeper"], # for current season
            "pointsDefenders": user_stats["seasons"][0]["pointsDefenders"], # for current season
            "pointsMidFielders": user_stats["seasons"][0]["pointsMidFielders"], # for current season
            "pointsForwards": user_stats["seasons"][0]["pointsForwards"], # for current season
            "combinedTransfers": user_stats["seasons"][0]["bought"] + user_stats["seasons"][0]["sold"], # for current season
            # "avgGoalKeeper": user_stats["seasons"][0]["averageGoalKeeper"],
            # "avgDefenders": user_stats["seasons"][0]["averageDefenders"],
            # "avgMidFielders": user_stats["seasons"][0]["averageMidFielders"],
            # "avgForwards": user_stats["seasons"][0]["averageForwards"],
        })            

    logging.info("Got league user stats.\n")

    with open("/code/frontend/src/data/league_user_stats.json", "w") as f:
        f.write(json.dumps(final_user_stats, indent=2))
        logging.debug("Created file league_user_stats.json")

    ### Timestamp for frontend
    with open("/code/frontend/src/data/timestamps/ts_league_user_stats.json", "w") as f:
        f.writelines(json.dumps({'time': datetime.now(tz=miscellaneous.TIMEZONE_DE).isoformat()}))
        logging.debug("Created file ts_league_user_stats.json")


def live_points(user_token, league_info):
    logging.info("Getting live points...")

    ### Get the current live points
    live_points = leagues.live_points(user_token, league_info[0].id)

    ### Create a custom json dict for every user and his players
    final_live_points = []

    for user in live_points["u"]:
        ### Create a custom json dict for every player of the user
        players = []

        for player in user["pl"]:
            players.append({
                "playerId": player["id"],
                "teamId": player["tid"],
                "firstName": player.get("fn", ""),  # Use an empty string if "fn" is not present
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
            "userId": user["id"],
            "userName": user["n"],
            # Profile Pic?
            "livePoints": user["t"],
            "totalPoints": user["st"],
            "players": players,
        })

    logging.info("Got live points.\n")

    with open("/code/frontend/src/data/live_points.json", "w") as f:
        f.write(json.dumps(final_live_points, indent=2))
        logging.debug("Created file live_points.json")

    ### Timestamp for frontend
    with open("/code/frontend/src/data/timestamps/ts_live_points.json", "w") as f:
        f.writelines(json.dumps({'time': datetime.now(tz=miscellaneous.TIMEZONE_DE).isoformat()}))
        logging.debug("Created file ts_live_points.json")


### -------------------------------------------------------------------
### -------------------------------------------------------------------
### -------------------------------------------------------------------


if __name__ == "__main__":
    ### Try to get the logins and Discord URL from the environment variables (Docker)
    kb_mail = getenv("KB_MAIL")
    kb_password = getenv("KB_PASSWORD")
    discord_webhook = getenv("DISCORD_WEBHOOK")

    ### Try to get the logins and Discord URL from the start arguments (local)
    parser = argparse.ArgumentParser(description="A free alternative to Kickbase Member/Pro.")
    parser.add_argument("-u", "--usermail", help="Your Kickbase E-Mail.")
    parser.add_argument("-p", "--password", help="Your Kickbase password.")
    parser.add_argument("-d", "--discord", help="Your Discord Webhook URL.")
    args = parser.parse_args()

    ### -------------------------------------------------------------------

    tprint("\n\nKB-Insights")
    print("\x1B[3mby casudo\x1B[0m\n\n")
    # print(f"\x1B[3m{VERSION}\x1B[0m\n\n")    

    start_time = time.time()

    main()

    ### Timestamp for frontend
    with open("/code/frontend/src/data/timestamps/ts_main.json", "w") as f:
        f.writelines(json.dumps({'time': datetime.now(tz=miscellaneous.TIMEZONE_DE).isoformat()}))
        logging.debug("Created file ts_main.json")

    elapsed_time_seconds = time.time() - start_time
    minutes = int(elapsed_time_seconds // 60)
    seconds = int(elapsed_time_seconds % 60)
    logging.info(f"DONE! Execution time: {minutes}m {seconds}s")