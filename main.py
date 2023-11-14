from kickbase import exceptions, profile, miscellaneous
from kickbase import __author__, __version__

### -------------------------------------------------------------------

def main():
    try:
        ### Login
        print("Logging in...\n")
        user, leagues, token = profile.login("YOUR_USER", "YOUR_PW")
        
        ### DEBUG
        print(user.name)
        print(leagues[0].name)
        print(leagues[0].pub)
        print(token)

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
    print(f"Running {__version__} by {__author__}\n\n") # print version from kickbase/__init__.py
    main()