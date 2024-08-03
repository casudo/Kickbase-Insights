import subprocess

from os import getenv, chdir
from time import sleep
from croniter import croniter
from datetime import datetime

### ===============================================================================

### Convert RUN_SCHEDULE (cron expression) to a valid date. Only run the python script (main.py) when the cron expression is met.
### TODO: This works, but isnt beatiful. 
def convert_cron_to_timestamp(cron_expression):
    current_time = datetime.now()
    # print(f"DB: DEF -> current time: {current_time}")
    cron = croniter(cron_expression, current_time)
    next_execution = cron.get_next(datetime)
    # print("DB: DEF -> next execution: ", next_execution)
    return next_execution.timestamp()

### ===============================================================================

### Get the environment variables
KB_MAIL = getenv("KB_MAIL")
KB_PASSWORD = getenv("KB_PASSWORD")
KB_LIGA = getenv("KB_LIGA")
DISCORD_WEBHOOK = getenv("DISCORD_WEBHOOK")
RUN_SCHEDULE = getenv("RUN_SCHEDULE", "10 2,6,10,14,18,22 * * *")
### 10 */8 * * * -> At minute 10 past every 8th hour
### 10 2,6,10,14,18,22 * * * -> At minute 10 past every 4th hour starting from 2am
WATCHPACK_POLLING = getenv("WATCHPACK_POLLING", "true")
START_DATE = getenv("START_DATE")
START_MONEY = getenv("START_MONEY", "50000000")

### Display a welcoming message in Docker logs
print("👍 Container started. Welcome!")
print("⏳ Checking environment variables...")

### Check if the environment variables are set
### Required Kickbase Account
if KB_MAIL is None or KB_PASSWORD is None:
    print("  ❌ Your Kickbase credentials are not fully set. Exiting...")
    exit()
else:
    print("  ✅ Your Kickbase credentials are set.")
    
### Optional preferred league name
if KB_LIGA:
    print(f"  ✅ Your preferred league name is set: {KB_LIGA}")
else:
    print("  ⚠️ No preferred league set, using default one.")

### Discord Webhook URL
if DISCORD_WEBHOOK is None:
    print("  ❌ DISCORD_WEBHOOK is not set. Exiting...")
    exit()
else:
    print("  ✅ DISCORD_WEBHOOK is set.")

### Check if RUN_SCHEDULE is using the default value
if RUN_SCHEDULE == "10 2,6,10,14,18,22 * * *":
    print("  ✅ Using default value for RUN_SCHEDULE:", RUN_SCHEDULE)
else:
    print("  ⚠️ RUN_SCHEDULE has been set to a custom value:", RUN_SCHEDULE)

### Check if WATCHPACK_POLLING is set by user
if WATCHPACK_POLLING == "true":
    print("  ✅ WATCHPACK_POLLING is set to true.")
else:
    print("  ✅ Using default value for WATCHPACK_POLLING.")

### Check if START_DATE is set by user
if START_DATE is None:
    print("  ❌ START_DATE is not set. Exiting...")
    exit()
else:
    try:
        ### Attempt to parse the date string to ensure it is in the correct format
        parsed_date = datetime.strptime(START_DATE, "%d.%m.%Y")
        print(f"  ✅ START_DATE is set to '{START_DATE}'.")
    except ValueError:
        print("  ❌ START_DATE format is incorrect. Please use 'DD.MM.YYYY'. Exiting...")
        exit()

### Check if START_MONEY is set
if START_MONEY == "50000000":
    formatted_money = f"{int(START_MONEY):,}".replace(",", ".") + "€"
    print(f"  ✅ Using game mode 'Auslosung' with {formatted_money} as starting money.")
elif START_MONEY == "200000000":
    formatted_money = f"{int(START_MONEY):,}".replace(",", ".") + "€"
    print(f"  ✅ Using game mode 'Ohne Team' with {formatted_money} as starting money.")
else:
    print("  ❌ START_MONEY is not set to a valid value. Exiting...")
    exit()

### ===============================================================================

# print("\nDEBUG ep.py: Running main")
subprocess.run(["python3", "-u", "/code/main.py"])

# print("\nDEBUG ep.py: Changing directiry")
chdir("/code/frontend")
# print("\nDEBUG ep.py: npm install")
subprocess.run(["npm", "install"])
# subprocess.run(["npm", "install", "jest"])

# print("\nDEBUG ep.py: npm start")
npm_process = subprocess.Popen(["npm", "start"])

### Sleep here to give the frontend time to start
sleep(120)

# print("\nDEBUG ep.py: Changing directiry")
chdir("/code/")
# print("\nDEBUG ep.py: Starting flask api")
flask_api = subprocess.Popen(["python3", "-u", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"])

### Sleep here to give the flask server time to start
sleep(120)

next_execution_timestamp = convert_cron_to_timestamp(RUN_SCHEDULE)
# print(f"DB: WHILE -> next execution timestamp: {next_execution_timestamp}")
while True:
    current_time_timestamp = datetime.now().timestamp()
    # print(f"DB: WHILE -> current time timestamp: {current_time_timestamp}") 
    
    if current_time_timestamp >= next_execution_timestamp:
        ### Run the python script (auto_entry.py)
        print("\n  🚀 Running main.py...\n\n")
        ### TODO: Log output
        subprocess.run(["python3", "-u", "/code/main.py"])
        
        next_execution_timestamp = convert_cron_to_timestamp(RUN_SCHEDULE)
        # print(f"DB: WHILE -> next execution timestamp: {next_execution_timestamp}")
    else:
        ### Log the next scheduled execution time
        next_execution_readable = datetime.fromtimestamp(next_execution_timestamp).strftime('%A, %B %d, %Y %I:%M %p')
        print("\n\n▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼")
        print(f"👀 Next execution will be on: {next_execution_readable}")
        print("▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲")

        ### Sleep until the next scheduled time
        sleep_duration = next_execution_timestamp - current_time_timestamp
        # print("DB: WHILE -> sleeping for: ", sleep_duration)
        sleep(sleep_duration)