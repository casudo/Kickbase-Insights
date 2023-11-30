from os import getenv, chdir
from time import sleep
from croniter import croniter
from datetime import datetime
import subprocess

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
DISCORD_WEBHOOK = getenv("DISCORD_WEBHOOK")
RUN_SCHEDULE = getenv("RUN_SCHEDULE", "10 2,6,10,14,18,22 * * *")
### 10 */8 * * * -> At minute 10 past every 8th hour
### 10 2,6,10,14,18,22 * * * -> At minute 10 past every 4th hour starting from 2am

### ===============================================================================

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

### ===============================================================================

print("DEBUG ep.py: Running main")
subprocess.run(["python3", "-u", "/code/main.py"])
# sleep??

print("DEBUG ep.py: Changing directiry")
chdir("/code/frontend")

print("DEBUG ep.py: npm install")
subprocess.run(["npm", "install"])

print("DEBUG ep.py: npm start")
# subprocess.run(["npm", "start"])
npm_process = subprocess.Popen(["npm", "start"])

### Sleep here to give the frontend time to start
sleep(300)

next_execution_timestamp = convert_cron_to_timestamp(RUN_SCHEDULE)
# print(f"DB: WHILE -> next execution timestamp: {next_execution_timestamp}")
while True:
    current_time_timestamp = datetime.now().timestamp()
    # print(f"DB: WHILE -> current time timestamp: {current_time_timestamp}") 
    
    if current_time_timestamp >= next_execution_timestamp:
        ### Run the python script (auto_entry.py)
        print("  🚀 Running main.py...\n\n")
        ### TODO: Log output
        subprocess.run(["python3", "-u", "/code/main.py"])
        
        next_execution_timestamp = convert_cron_to_timestamp(RUN_SCHEDULE)
        # print(f"DB: WHILE -> next execution timestamp: {next_execution_timestamp}")
    else:
        ### Log the next scheduled execution time
        next_execution_readable = datetime.fromtimestamp(next_execution_timestamp).strftime('%A, %B %d, %Y %I:%M %p')
        print("\n\n▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼")
        print(f"👀 Next execution will be on: {next_execution_readable}")
        print("▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲")

        ### Sleep until the next scheduled time
        sleep_duration = next_execution_timestamp - current_time_timestamp
        # print("DB: WHILE -> sleeping for: ", sleep_duration)
        sleep(sleep_duration)