from kickbase import exceptions, user, miscellaneous, leagues
from kickbase import __author__, __version__

from pprint import pprint
import json

### -------------------------------------------------------------------

def main():
    try:
        ### Login
        print("Logging in...\n")
        user_info, league_info, user_token = user.login("fakefrank5@web.de", "Wasser30lol_")
        
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
            if player.username:
                ### Create a custom json dict for every player listed by real users
                players_listed_by_user.append({
                    "id": player.id,
                    "firstName": f"{player.firstName}", 
                    "lastName": f"{player.lastName}",
                    "price": player.price,
                    "listedBy": f"{player.username}",
                })
            else:
                ### Create a custom json dict for every player listed by kickbase
                players_listed_by_kickbase.append({
                    "id": player.id,
                    "firstName": f"{player.firstName}", 
                    "lastName": f"{player.lastName}",
                    "price": player.price,
                })
        ### Write the json dicts to a file. These will be read by the frontend.
        with open("market_players.json", "w") as f:
            f.write(json.dumps(players_listed_by_user, indent=2))
        with open("market_kickbase.json", "w") as f:
            f.write(json.dumps(players_listed_by_kickbase, indent=2))
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