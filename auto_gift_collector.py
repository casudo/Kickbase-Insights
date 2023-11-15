from kickbase import user, miscellaneous, exceptions, leagues

import argparse

### -------------------------------------------------------------------

parser = argparse.ArgumentParser(description="Kickbase Test Desc")
parser.add_argument("-u", "--email", required=True, help="Kickbase email")
parser.add_argument("-p", "--password", required=True, help="Kickbase password")
parser.add_argument("-d", "--discord", required=True, help="Discord webhook url")
args = parser.parse_args()

def main():
    try:
        ### Login
        print("Logging in...\n")
        user_info, league_info, user_token = user.login(args.email, args.password)

        print("\n\n=====================================")
        print(f"Successfully logged in as {user_info.name}.\n")
        # miscellaneous.discord_notification("Kickbase Login", f"Successfully logged in as {user.name}.", 6617600)
        print(f"Available leagues: {', '.join([league.name for league in league_info])}\n") # Print all available leagues the user is in
    
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
    except exceptions.LoginException as e:
        print(e)
        return
    except exceptions.NotificatonException as e:
        print(e)
        return
    

### -------------------------------------------------------------------
### -------------------------------------------------------------------
### -------------------------------------------------------------------

if __name__ == "__main__":    
    if args.email and args.password and args.discord:
        main()
    else:
        print("Please enter all arguments!")
        exit()