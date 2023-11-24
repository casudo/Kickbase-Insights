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
        print("=====FEED END=====")

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
        with open("frontend/data/market_players.json", "w") as f:
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