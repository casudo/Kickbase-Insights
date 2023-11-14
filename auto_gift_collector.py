from kickbase import profile, miscellaneous, exceptions

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
        user, leagues, token = profile.login(args.email, args.password)

        print(f"Successfully logged in as {user.name}.")
        print(f"Available leagues: ")
        for league in leagues:
            print(league.name)
        # miscellaneous.discord_notification("Kickbase Login", f"Successfully logged in as {user.name}.", 6617600)
    
        ### Gift
        gift = miscellaneous.is_gift_available(token, leagues[0].id)
        ### Check if dict in gift has {'isAvailable': True}:
        if gift["isAvailable"]:
            print("Gift available!")
            print(gift)
            miscellaneous.discord_notification("Kickbase Gift available!", f"Amount: {gift['amount']}\nLevel: {gift['level']}", 6617600)
            miscellaneous.get_gift(token, leagues[0].id) # TODO: Try, except needed here?
        else:
            print("Gift not available!")
            print(gift)
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