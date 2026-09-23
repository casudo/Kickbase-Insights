import logging

from os import getenv, path
from flask import Flask, jsonify
from flask_cors import CORS

from backend import exceptions
from backend.kickbase.v4 import competitions, user, leagues
from backend.paths import DATA_DIR

import main

# ===============================================================================

kb_mail = getenv("KB_MAIL")
kb_password = getenv("KB_PASSWORD")
discord_webhook = getenv("DISCORD_WEBHOOK")
preferred_league_name = getenv("KB_LIGA")

# ===============================================================================

app = Flask(__name__)
CORS(app)


@app.route("/api/livepoints", methods=["GET"])
def get_live_points():
    logging.info("Flask API: Getting live points...")

    try:
        # Login to Kickbase
        user_info, user_token = user.login(
            kb_mail,
            kb_password,
            discord_webhook
        )

        # Get leagues
        league_list = leagues.get_league_list(user_token)

        if not league_list:
            return jsonify({"error": "No leagues found."}), 404

        # Select preferred league
        selected_league = next(
            (
                league
                for league in league_list
                if league.name == preferred_league_name
            ),
            league_list[0]
        )

        # Clear cached API data
        competitions.clear_caches()

        # ---------------------------------------------------------------
        # Make sure the files required by live_points() exist.
        # Railway may not have these files after a fresh deployment.
        # ---------------------------------------------------------------

        taken_players_file = path.join(
            DATA_DIR,
            "taken_players.json"
        )

        league_stats_file = path.join(
            DATA_DIR,
            "league_user_stats.json"
        )

        if not path.exists(taken_players_file):
            logging.info(
                "taken_players.json missing - generating it..."
            )

            main.taken_free_players(
                user_token,
                selected_league
            )

        if not path.exists(league_stats_file):
            logging.info(
                "league_user_stats.json missing - generating it..."
            )

            main.league_user_stats_tables(
                user_token,
                selected_league
            )
leagues.get_users(user_token, selected_league.id)
        # live_points() only needs the user token
        final_live_points = main.live_points(user_token)

        return jsonify(final_live_points)

    except exceptions.KickbaseException as e:
        logging.exception(
            "Flask API: Kickbase error while getting live points"
        )

        return jsonify({
            "error": str(e)
        }), 502

    except Exception as e:
        logging.exception(
            "Flask API: Unexpected error while getting live points"
        )

        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(getenv("PORT", 3000))
    )
