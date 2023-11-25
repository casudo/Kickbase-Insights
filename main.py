from kickbase import exceptions, user, miscellaneous, leagues, competition
from kickbase import __author__, __version__

from pprint import pprint
import json
from datetime import datetime, timedelta

### -------------------------------------------------------------------

def main():
    try:
        ### Login
        print("Logging in...\n")
        user_info, league_info, user_token = user.login("user", "pass")
        
        ### DEBUG
        print("\n\n### DEBUG")
        print(user_info.name)
        print(league_info[0].name)
        print(league_info[0].pub)
        print(user_token)
        print("\n\n")

        print("\n\n=====================================")
        print(f"Successfully logged in as {user_info.name}.\n")
        # miscellaneous.discord_notification("Kickbase Login", f"Successfully logged in as {user.name}.", 6617600)
        print(f"Available leagues: {', '.join([league.name for league in league_info])}\n") # Print all available leagues the user is in


        ### TODO: Print stats for the leagues here

        ### TODO: For loop for every league?
        ### Gift
        gift = leagues.is_gift_available(user_token, league_info[0].id)
        ### Check if dict in gift has {'isAvailable': True}:
        if gift["isAvailable"]:
            print(f"Gift available in league {league_info[0].name}!\n")
            miscellaneous.discord_notification("Kickbase Gift available!", f"Amount: {gift['amount']}\nLevel: {gift['level']}", 6617600)
            leagues.get_gift(user_token, league_info[0].id) # TODO: Try, except needed here?, TODO: Check response
        else:
            print(f"Gift has already been collected in league {league_info[0].name}!\n")
            miscellaneous.discord_notification("Kickbase Gift not available!", f"Gift not available!", 6617600) # TODO: Change color   

        ### =====================================================================================================
        ### League stuff
        league_user_info = leagues.league_user_info(user_token, league_info[0].id)
        print(f"=== Statistics for {user_info.name} in league {league_info[0].name} ===")
        print(f"Budget: {league_user_info.budget}€")
        print(f"Team value: {league_user_info.teamValue}€")
        print(f"Points: {league_user_info.points}")
        print(f"Rank: {league_user_info.placement}")

        ### ---------- Feed ----------
        league_feed = leagues.league_feed(user_token, league_info[0].id)
        ### Loop through all feed entries and print them
        print("=====FEED START=====")
        for feed_entry in league_feed:
            print("------------------------")
            print(f"| {feed_entry.meta.pfn} {feed_entry.meta.pln}") # | Manuel Neuer
            if feed_entry.type == 3: # Type 3 = Listed by Kickbase
                print(f"| Listed since: {feed_entry.age}") # | Listed since: 435345
            if feed_entry.type == 12: # Type 12 = Player bought from Kickbase
                print(f"| Sold for: {feed_entry.meta.p}€ to {feed_entry.meta.bn} from Kickbase") # | Sold for: 5000561€ to Frank from Kickbase
            ### TODO: Player bought from Player
            ### TODO: Player sold to Kickbase
        # print("=====FEED END=====")

        ### TODO: Player Info, Feed (?), Points, Stats

        ### TODO: Feed (?), Info, Stats, Users, User Profile and Stats (?), Me (?), Quickstats (?)

        ### TODO: Remove & add player to market, accept & decline offer, update price (?), place & remove offer 

        ### ---------- Market ----------
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
                    "trend": player.marketValueTrend,
                    "expiration": (datetime.now() + timedelta(seconds=player.expiry)).strftime('%d.%m.%Y %H:%M:%S'),
                })
            else:
                ### Create a custom json dict for every player listed by kickbase
                players_listed_by_user.append({
                    "teamId": player.teamId,
                    "position": miscellaneous.POSITIONS[player.position],
                    "firstName": f"{player.firstName}", 
                    "lastName": f"{player.lastName}",
                    "price": player.price,
                    "trend": player.marketValueTrend,
                    "seller": player.username,
                    "expiration": (datetime.now() + timedelta(seconds=player.expiry)).strftime('%d.%m.%Y %H:%M:%S'),
                })
        ### Write the json dicts to a file. These will be read by the frontend.
        with open("frontend/data/market_user.json", "w") as f:
            f.write(json.dumps(players_listed_by_user, indent=2))
        with open("frontend/data/market_kickbase.json", "w") as f:
            f.write(json.dumps(players_listed_by_kickbase, indent=2))
        ### ----------------------------


        ### ---------- Market Value Changes ----------
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
        ### Write the json dicts to a file. These will be read by the frontend.
        with open("frontend/data/market_value_changes.json", "w") as f:
            f.write(json.dumps(players_LIST, indent=2))
        ### ----------------------------


        ### ---------- Taken & Free Players ----------
        ### To get the taken players, we first cycle through the individual users BUY/SELL feed to determine which players are bought by the user.
        ### In case a player was assigned to the user on league join, the player is not in the BUY/SELL feed.
        ### To indicate these players, we cycle through ALL players of a team and check if the player is owned by a user.

        ### We start by cycling through the users BUY/SELL feed. The players will be stored in the below list.
        user_transfers_result = []

        ### After that, we check the teams for starter players.
        team_players_result = []

        ### The final results of both lists will be combined into the final_result list below.
        final_result = []

        ### Get all users in the league
        league_users = leagues.league_users(user_token, league_info[0].id)
        # print(f"DEBUG of USERS: {league_users['users'][0]}")

        ### Loop through all users in the league
        for real_user in league_users.get("users"):
            print(f"\n\nDEBUG Username: {real_user['name']}")
            print("DEBUG: Real user id: " + str(real_user["id"]))

            taken_players = []
            user_has_sold = set()

            ### Get all transfers of a user
            user_transfers = leagues.user_players(user_token, league_info[0].id, real_user["id"])
            print(f"DEBUG: Found {len(user_transfers)} transfers for user {real_user['name']}")

            ### Loop through all transfers of a user (done by getting the user specific BUY/SELL feed)
            for transfer in user_transfers:
                ### Search the stats of the given player ID to fill the missing attributes for the player which cannot be found in the BUY/SELL feed
                player_stats = leagues.player_statistics(user_token, league_info[0].id, transfer["meta"]["pid"])
                # print(f"DEBUG: Player stats: {player_stats['position']}")

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
                    print(f"DEBUG: Player {player.p.firstName} {player.p.lastName} isn't on the list of taken players, but is owned by user {player_stats.get('userName')}!")

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
                        "trend": player_stats["mvTrend"],
                    })

        ### Now we add the list of both checks to the final_result list.
        team_players_result += starter_players
        final_result = (user_transfers_result + team_players_result) 
        
        ### Write the json dicts to a file. These will be read by the frontend.
        with open("frontend/data/taken_players.json", "w") as f:
            f.write(json.dumps(final_result, indent=2))

        ### Based on all taken players, we can now get all free players
        miscellaneous.get_free_players(user_token, league_info[0].id, final_result)

        ### ----------------------------
        














    except exceptions.LoginException as e:
        print(e)
        return
    except exceptions.NotificatonException as e:
        print(e)
        return
    except exceptions.KickbaseException as e:
        print(e)
        return
    

### -------------------------------------------------------------------
### -------------------------------------------------------------------
### -------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Running {__version__} by {__author__}\n\n") # print version from kickbase/__init__.py

    main()