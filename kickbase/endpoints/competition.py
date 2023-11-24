"""
### This file contains all models for the competition endpoint.

Endpoint:
`/competition/...`
"""


### ===============================================================================
### Team Players stuff

class P:
    """
    ### Create an object for the team players with all its attributes.

    The JSON response for the feed entries looks like this:
    ```json  
    {
        "p": [
            {
                "id": "237",
                "teamId": "2",
                "teamName": "Bayern",
                "teamSymbol": "FCB",
                "firstName": "Manuel",
                "lastName": "Neuer",
                "profile": "https://kickbase.b-cdn.net/pool/players/237.jpg",
                "profileBig": "https://kickbase.b-cdn.net/pool/playersbig/237.png",
                "team": "https://kickbase.b-cdn.net/team/2013/07/30/3ebe44c53c3f4c87bd605da69e743fb8.jpg",
                "teamCover": "https://kickbase.b-cdn.net/team/2013/08/01/ec8377d89197450e89fa942e4e36d48c.png",
                "status": 0,
                "position": 1,
                "number": 1,
                "averagePoints": 127,
                "totalPoints": 381,
                "marketValue": 19422256.0,
                "marketValueTrend": 1
            },
            { ... },
        ]
    }
    ```
    """
    id: str = None
    teamId: str = None
    teamName: str = None
    teamSymbol: str = None
    firstName: str = None
    lastName: str = None
    profile: str = None # Somehow not always present e.g. Jamal Musiala
    profileBig: str = None
    team: str = None # Somehow not always present
    teamCover: str = None # Somehow not always present
    status: int = None
    position: int = None
    number: int = None
    averagePoints: int = None
    totalPoints: int = None
    marketValue: float = None
    marketValueTrend: int = None

    def __init__(self, p_dict: dict):
        self.id = p_dict["id"]
        self.teamId = p_dict["teamId"]
        self.teamName = p_dict["teamName"]
        self.teamSymbol = p_dict["teamSymbol"]
        self.firstName = p_dict["firstName"]
        self.lastName = p_dict["lastName"]
        if "profile" in p_dict:
            self.profile = p_dict["profile"]
        self.profileBig = p_dict["profileBig"]
        if "team" in p_dict:
            self.team = p_dict["team"]
            self.teamCover = p_dict["teamCover"]
        self.status = p_dict["status"]
        self.position = p_dict["position"]
        self.number = p_dict["number"]
        self.averagePoints = p_dict["averagePoints"]
        self.totalPoints = p_dict["totalPoints"]
        self.marketValue = p_dict["marketValue"]
        self.marketValueTrend = p_dict["marketValueTrend"]


class Team_Players:
    """
    ### Create an object for the team players with all its attributes.

    Used for endpoint URL:
    `/competition/teams/[team_id]/players` -> get all players of a given team
    """
    ### No attributes here!

    def __init__(self, team_players_dict: dict):
        self.p = P(team_players_dict)

### End of Team Players stuff
### ===============================================================================


# class Search_Competition_Players: 
#     """
#     ### TODO: Change me
#
#     Used for endpoint URL:
#     `/competition/search?query=` -> TODO: Change me
#     """

# class Top_25_Players: 
#     """
#     ### TODO: Change me
#
#     Used for endpoint URL:
#     `/competition/best?position=0` -> TODO: Change me
#     """

# class Matches: 
#     """
#     ### TODO: Change me
#
#     Used for endpoint URL:
#     `/competition/matches?matchDay=<MATCH_DAY_NR>` -> TODO: Change me
#     """

# class Table: 
#     """
#     ### TODO: Change me
#
#     Used for endpoint URL:
#     `/competition/table?matchDay=<MATCH_DAY_NR>` -> TODO: Change me
#     """

# class Search_Players: 
#     """
#     ### TODO: Change me
#
#     Used for endpoint URL:
#     `/competition/search?t=Lewandowski` -> TODO: Change me
#     """