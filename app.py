import logging, json, os
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS

from backend import miscellaneous
from backend.kickbase.v1 import leagues, user

### ===============================================================================

### Get the needed environment variables
mail = os.getenv('KB_MAIL')
password = os.getenv('KB_PASSWORD')

### ===============================================================================

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

@app.route('/api/livepoints', methods=['GET'])
def get_live_points():
    print("Flask API: Getting live points...")

    ### Login to Kickbase
    user_info, league_info, user_token = user.login(mail, password)

    ### Get the current live points
    live_points = leagues.live_points(user_token, league_info[0].id)

    ### Create a custom json dict for every user and his players
    final_live_points = []

    for users in live_points["u"]:
        ### Create a custom json dict for every player of the user
        players = []

        for player in users["pl"]:
            players.append({
                "playerId": player["id"],
                "teamId": player["tid"],
                "firstName": player.get("fn", ""),  # Use an empty string if "fn" is not present
                "lastName": player["n"],
                "number": player["nr"],
                "points": player["t"],
                "goals": player["g"],
                "assists": player["a"],
                "redCards": player["r"],
                "yellowCards": player["y"],
                "yellowRedCards": player["yr"],
                ### Custom attributes for the frontend
                "fullName": f"{player.get('fn', '')} {player['n']} ({player['nr']})",
            })

        final_live_points.append({
            "userId": users["id"],
            "userName": users["n"],
            # Profile Pic?
            "livePoints": users["t"],
            "totalPoints": users["st"],
            "players": players,
        })

    print("Flask API: Got live points.\n")

    with open("/code/frontend/src/data/live_points.json", "w") as f:
        f.write(json.dumps(final_live_points, indent=2))
        logging.debug("Created file live_points.json")

    ### Timestamp for frontend
    with open("/code/frontend/src/data/timestamps/ts_live_points.json", "w") as f:
        f.writelines(json.dumps({'time': datetime.now(tz=miscellaneous.TIMEZONE_DE).isoformat()}))
        logging.debug("Created file ts_live_points.json")

    ### Return the live points
    return jsonify(final_live_points)

if __name__ == '__main__':
    app.run()