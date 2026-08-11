import logging

from os import getenv
from flask import Flask, jsonify
from flask_cors import CORS

import main
from backend import exceptions
from backend.kickbase.v4 import leagues, user

### ===============================================================================

### Get the needed environment variables
kb_mail = getenv("KB_MAIL")
kb_password = getenv("KB_PASSWORD")
discord_webhook = getenv("DISCORD_WEBHOOK")

### ===============================================================================

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

@app.route("/api/livepoints", methods=["GET"])
def get_live_points():
    """### Fetches the current live points and returns them to the frontend.

    The payload is built by `main.live_points()`, which also writes `live_points.json`
    and its timestamp into the frontend data directory.

    NOTE: The live points feature is on-hold, so the underlying Kickbase endpoint is
    unverified against the current API.
    """
    logging.info("Flask API: Getting live points...")

    try:
        ### Login to Kickbase
        user_info, user_token = user.login(kb_mail, kb_password, discord_webhook)

        ### Get all leagues the user is in and pick the one to show data for
        league_list = leagues.get_league_list(user_token)
        if not league_list:
            logging.error("Flask API: No leagues found.")
            return jsonify({"error": "No leagues found for this Kickbase account."}), 502
        selected_league = main.select_league(league_list)

        ### Get the current live points (also writes live_points.json + timestamp)
        final_live_points = main.live_points(user_token, selected_league)
    except exceptions.LoginException as e:
        logging.error(f"Flask API: {e}")
        return jsonify({"error": "Login failed! Please check your credentials."}), 502
    except exceptions.KickbaseException as e:
        logging.error(f"Flask API: {e}")
        return jsonify({"error": "Couldn't get the live points from Kickbase."}), 502

    logging.info("Flask API: Got live points.")

    ### Return the live points
    return jsonify(final_live_points)

if __name__ == "__main__":
    app.run()
