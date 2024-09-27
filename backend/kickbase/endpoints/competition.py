"""
### This file contains all models for the competition endpoint, regardless of the API version.

#### Endpoint:
`/vX/competition/...`
"""

class Player:
    """
    ### Create an object for a player with all its attributes.

    Used for endpoint URL:
    `/competition/teams/[team_id]/players` -> get all players of a given team
    """

    def __init__(self, p_dict: dict):
        self.id: str = p_dict.get("id", None)
        self.teamId: str = p_dict.get("teamId", None)
        self.teamName: str = p_dict.get("teamName", None)
        self.teamSymbol: str = p_dict.get("teamSymbol", None)
        self.firstName: str = p_dict.get("firstName", None)
        self.lastName: str = p_dict.get("lastName", None)
        self.profile: str = p_dict.get("profile", None)  ### Not always present
        self.profileBig: str = p_dict.get("profileBig", None)  ### Not always present
        self.team: str = p_dict.get("team", None)  ### Not always present
        self.teamCover: str = p_dict.get("teamCover", None)  ### Not always present
        self.status: int = p_dict.get("status", None)
        self.position: int = p_dict.get("position", None)
        self.number: int = p_dict.get("number", None)
        self.averagePoints: int = p_dict.get("averagePoints", None)
        self.totalPoints: int = p_dict.get("totalPoints", None)
        self.marketValue: float = p_dict.get("marketValue", None)
        self.marketValueTrend: int = p_dict.get("marketValueTrend", None)