<div align="center">
  <a href="https://de.kickbase.com/"><img width="400" alt="Logo" src="repo_pictures/kickbase.jpg"></a>
  <br>
  <h1>Kickbase Insights</h1>
  This project is a used to gather data from <a href="https://www.kickbase.com/">Kickbase</a> API endpoint and visualize it in a web interface, acting as alternative for the pro/member membership.

  ---

  <!-- Placeholder for badges -->
  ![GitHub License](https://img.shields.io/github/license/casudo/kickbase-insights) ![GitHub release (with filter)](https://img.shields.io/github/v/release/casudo/kickbase-insights)


</div>

> [!NOTE]
This is a hobby project to test stuff with JSON and the cores of Python. Feel free to create issues and contribute.  

##### Table of Contents
- [Screenshots](#screenshots)
- [Docker](#docker)
  - [docker run](#docker-run)
  - [Docker Compose](#docker-compose)
- [Development](#development)
- [Planned for the future](#planned-for-the-future)
- [Thanks to](#thanks-to)
- [License](#license)

---

## Screenshots
You can find some screenshots of the frontend below, not all features are shown.  

> [!WARNING]
As of v1.4.0  

![Transfers](repo_pictures/transfers.png)  
![MarketValue](repo_pictures/marketvalue.png)  
![Revenue](repo_pictures/revenue.png)  
![LivePoints](repo_pictures/livepoints.png)  

## Docker
If you want to run this in a Docker container, you'll first need to set some mandatory environment variables:  

| Variable | Required | Description |
| --- | --- | --- |
| `KB_MAIL` | **Yes** | Your Kickbase E-Mail. |
| `KB_PASSWORD` | **Yes** | Your Kickbase password. |
| `KB_LIGA` | No | The name of the league you want to see data for in the GUI. If not set, defaults to the first league you're in. |
| `DISCORD_WEBHOOK` | **Yes** | The Discord webhook URL to send notifications to. |
| `RUN_SCHEDULE` | No | The cron expression when the script should fetch new information from the API. If not set, defaults to `10 2,6,10,14,18,22 * * *`. |
| `START_DATE` | **Yes** | The date when the season started in format `dd.mm.yyyy`. |
| `START_MONEY` | No | The amount of money you started with. If not set, defaults to 50.000.000€ |
| `TZ` | No | The timezone to use. Defaults to `Europe/Berlin` |

> [!IMPORTANT]
> The live points feature is currently on-hold and not present as of v2.4.0!
> To handle the re-implementation of the live points with more ease, the ports for the backend are not commented out.

### docker run
```bash
docker run -d \
    --name=kickbase_insights \
    --restart=unless-stopped \
    -p <frontend_port>:3000 -p <backend_port>:5000 \
    -e KB_MAIL=<kickbase_email> \
    -e KB_PASSWORD=<kickbase_password> \
    -e DISCORD_WEBHOOK=<discord_webhook> \
    -e START_DATE=<start_date> \
    ghcr.io/casudo/kickbase-insights:latest
```  

### Docker Compose
```yaml
version: "3.8"

services:
  kickbase-insights:
    image: ghcr.io/casudo/kickbase-insights:latest
    container_name: kickbase_insights
    restart: unless-stopped
    ports:
      - <frontend_port>:3000 # Web GUI
      - <backend_port>:5000 # Backend API (../api/livepoints)  
    environment:
      - KB_MAIL=<kickbase_email>
      - KB_PASSWORD=<kickbase_password>
      - DISCORD_WEBHOOK=<discord_webhook>
      - START_DATE=<start_date>
```  

---

If you run this container in your LAN (via IP), you'll need to change the following line in the `App.js` file in the `frontend/src` folder to this (obv. change `<backend_port>`):     
```js
const response = await fetch('http://localhost:<backend_port>/api/livepoints')
```  

If you make this container publically available via a domain, you'll need to create/update the following entry in your reverse proxy:  
`your.domain.com -> <container_ip_or_hostname>:3000`  
`your.domain.com/api/livepoints -> <container_ip_or_hostname>:5000`  
> [!IMPORTANT]
In order to this to work, both your reverse proxy and the container need to be in the same network.  

In Traefik, the dynamic config would look like this:  
```yaml
http:
  routers:
    kickbase-web:
      service: kickbase-web
      rule: Host(`your.domain.de`)
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

    kickbase-api:
      service: kickbase-api
      rule: Host(`your.domain.de`) && PathPrefix(`/api/livepoints`)
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

  services:
    kickbase-web:
      loadBalancer:
        servers:
          - url: http://<container_hostname>:3000

    kickbase-api:
      loadBalancer:
        servers:
          - url: http://<container_hostname>:5000
```

> [!NOTE]
It may take some time to initially start the container, so check the logs!  

---

## Development
If you want to contribute to this project, you can follow the steps below to jump right into the development environment.  
```bash
docker run -dit --name=Kickbase -p <frontend_port>:3000 -p <backend_port>:5000 -e KB_MAIL=<kickbase_mail> -e KB_PASSWORD=<kickbase_password> -e DISCORD_WEBHOOK=<discord_webhook> -e WATCHPACK_POLLING=true -e START_DATE=<start_date> ubuntu
```  
Run this long command to setup the container:  
```bash
mkdir /code && cd /code && apt update && apt upgrade -y && apt install tree nano python3 python3-pip git curl -y && git clone https://github.com/casudo/Kickbase-Insights.git . && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs && pip install --upgrade pip && pip install --upgrade -r requirements.txt && mkdir -p frontend/src/data/timestamps && mkdir logs && cd frontend && npm install
```  

If you have this project already cloned, you can run the following command to bind mount the files inside the container:  
```bash
docker run -dit --name=Kickbase -p <frontend_port>:3000 -p <backend_port>:5000 -e KB_MAIL=<kickbase_mail> -e KB_PASSWORD=<kickbase_password> -e DISCORD_WEBHOOK=<discord_webhook> -e WATCHPACK_POLLING=true -e START_DATE=<start_date> -v <your_folder>\Kickbase-Insights:/code ubuntu
```  
Run this long command to setup the container:  
```bash
cd /code && apt update && apt upgrade -y && apt install tree nano python3 python3-pip curl -y && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs && pip install --upgrade pip && pip install --upgrade -r requirements.txt && mkdir -p frontend/src/data/timestamps && mkdir logs && cd frontend && npm install
```  

Now you're ready to go. Keep in mind that you'll first need to run `main.py` to get the required data for the frontend.  
`python3 main.py`  

You'll also need to manually run `npm start` in the `frontend` folder as well as `python3 -u -m flask run --host=0.0.0.0 --port=5000` in the `/code` folder.  

---

## Planned for the future
**Frontend:**  
- Market table: Maybe add ligainsider rating?
- Add base features
  - Feed
  - Lineup
  - Next matches
  - League table
  - Top players
- Transfererlöse: Hold player for X days  
- Sum. Transfererlöse: Add custom scale for chart  
- Misc: Unsold starter players    
- Reformat changelog  
- Other menu layout (+ mobile responsive)  
- Back to top button  
- ToC on pages with lot of content  
- Market value graph for players  

**Backend:**  
- Fix all TODOs  
- Add best practice to seperate duplicate variables names from modules (e.g. user and user. Which one is the module and which one is the variable?)   
- Discord notifications  
- Logging module for entrypoint.py and app.py    
- Add linter/formatter  
- Categorize components to frontend menu    
- Battles: Spieltagsdominator: Fix placements being wrong for people with the same amount of mdWins  
- Change behavior if player has the position number of "0". Instead of defaulting that to "1", do smth else
- Support for multiple leagues via ports (League 1: 5000, League 2: 5001, etc.)

**Misc:**  
- Add Postman workspace  
- Add Workflow chart  
- Automatically disable caching  

---

### Thanks to
- [@roman-la](https://github.com/roman-la) for the base of the frontend  

---

### License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details