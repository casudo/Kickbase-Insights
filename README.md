> Note: This is a hobby project to test stuff with JSON and the cores of Python. Feel free to create issues and contribute.  

# Kickbase Insights
This project is a used to gather data from [Kickbase](https://www.kickbase.com/) API endpoint and automate various interactions. It is planned to add a nice GUI in the feature, acting as a dashboard for your Kickbase team.

##### Table of Contents
- [Docker](#docker)
  - [docker run](#docker-run)
  - [Docker Compose](#docker-compose)
- [Local usage](#local-usage)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
- [Planned for the future](#planned-for-the-future)
- [Thanks to](#thanks-to)
- [License](#license)

## Docker
If you want to run this in a Docker container, you'll first need to set some mandatory environment variables:  

| Variable | Required | Description |
| --- | --- | --- |
| `KB_MAIL` | **Yes** | Your Kickbase E-Mail. |
| `KB_PASSWORD` | **Yes** | Your Kickbase password. |
| `DISCORD_WEBHOOK` | **Yes** | The Discord webhook URL to send notifications to. |
| `RUN_SCHEDULE` | No | The cron expression when the script should fetch new information from the API. If not set, defaults to `10 2,6,10,14,18,22 * * *`. |
| `WATCHPACK_POLLING` | **Yes** | Used to [apply new changes](https://stackoverflow.com/a/72661752) in the filesystem on runtime. If not set, defaults to `true`. |

### docker run
```bash
docker run -d \
    --name=kickbase_insights \
    --restart=unless-stopped \
    -p <port>:3000 \
    -e KB_MAIL=<kickbase_email> \
    -e KB_PASSWORD=<kickbase_password> \
    -e DISCORD_WEBHOOK=<discord_webhook> \
    -e RUN_SCHEDULE=<your_schedule> \ 
    -e WATCHPACK_POLLING=true \
    ghcr.io/casudo/kickbase-insights:<tag>
```  

### Docker Compose
```yaml
version: "3.8"

services:
  kickbase-insights:
    image: ghcr.io/casudo/kickbase-insights:<tag>
    container_name: kickbase_insights
    restart: unless-stopped
    environment:
        - KB_MAIL=<kickbase_email>
        - KB_PASS=<kickbase_password>
        - DISCORD_WEBHOOK=<discord_webhook>
        - RUN_SCHEDULE=<your_schedule>
        - WATCHPACK_POLLING=true
```  

Save the above as `docker-compose.yml` and run it with `docker-compose up -d`.   

That's it.  

> Note: It may take some time to first run the container, so check the logs!  

## Local usage
To run Kickbase Insights on your local machine, you can follow the steps described below.  

### Prerequisites
- Python 3.X
- Pip
- Node.js
- NPM

### Installation
1. Download a release from the [releases page](https://github.com/casudo/Kickbase-Insights/releases) or clone the repository  
2. (Optional): Create a virtual environment for the python dependencies  
3. Install the python dependencies with `pip install -r requirements.txt`  
4. Run `main.py` with the required arguments (see below)  
    - To get a list of the required arguments, run `python main.py --help`  
5. Run the following commands in the `frontend` folder:  
    - `npm install`  
    - `npm start`  
6. Visit the GUI at `localhost:3000`  

## Planned for the future
**Frontend:**  
- Market table: Add fitness, maybe ligainsider rating?
- Lineup planner: Add fitness
- Add battles  
- Transfererlöse: Hold player for X days  
- Sum. Transfererlöse: Add custom scale for chart  
- Dev: Execution time  
- Misc: Unsold starter players    
- Display version from container image version   

**Backend:**  
- Fix all TODOs  
- Measure time of API calls and display them under Misc?  
- Add best practice to seperate duplicate variables names from modules (e.g. user and user. Which one is the module and which one is the variable?)  
- Fix TZ in Ubuntu image ([Stackoverflow](https://serverfault.com/questions/683605/docker-container-time-timezone-will-not-reflect-changes))  
- Discord notifications  
- Logging module for entrypoint.py  

**Misc:**  
- Add Postman workspace  
- Add Workflow chart  
- Add ./data, ./data/timestamp and logs/ folders to git  
- Automatically disable caching  

### Thanks to
- [@fabfischer](https://github.com/fabfischer) for the inspiration and the currently great and working [Kickbase+ web client](https://github.com/fabfischer/kickbase-plus)  
- [@kevinskyba](https://github.com/kevinskyba) for providing the excellent [Kickbase API documentation](https://kevinskyba.github.io/kickbase-api-doc)  
- [@roman-la](https://github.com/roman-la) for the base of the frontend  

### License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details