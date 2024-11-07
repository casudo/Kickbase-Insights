"""
### This file contains all models for the user endpoint, regardless of the API version.

#### Endpoint:
`/vX/user/...`
"""

class User:
    """
    ### This class will create on object with all user information given upon logging in.

    Used for endpoint URL:
    `/user/login` -> get all user data
    """
    def __init__(self, user_dict: dict):
        self.email: str = user_dict.get("email", None)
        self.cover: str = user_dict.get("cover", None)
        self.flags: int = user_dict.get("flags", None)
        self.vemail: str = user_dict.get("vemail", None)
        self.id: str = user_dict.get("id", None)
        self.name: str = user_dict.get("name", None)
        self.profile: str = user_dict.get("profile", None)


class League:
    """
    ### Create an object for a league with all its attributes.

    Used for endpoint URL:
    `/user/login` -> get all leagues the user is in
    """
    def __init__(self, league_dict: dict):
        self.id: str = league_dict.get("id", None)  ### League ID
        self.cpi: str = league_dict.get("cpi", None)
        self.name: str = league_dict.get("name", None)  ### League name
        self.creator: str = league_dict.get("creator", None)  ### League creator's username
        self.creatorId: str = league_dict.get("creatorId", None)  ### League creator's ID
        self.creation: str = league_dict.get("creation", None)  ### League creation date
        self.ai: str = league_dict.get("ai", None)
        self.t: str = league_dict.get("t", None)
        self.au: str = league_dict.get("au", None)
        self.mu: str = league_dict.get("mu", None)
        self.ap: str = league_dict.get("ap", None)  ### Not always present
        self.pub: str = league_dict.get("pub", None)
        self.gm: str = league_dict.get("gm", None)
        self.mpl: str = league_dict.get("mpl", None)
        self.ci: str = league_dict.get("ci", None)
        self.btlg: str = league_dict.get("btlg", None)  ### Not always present
        self.vr: str = league_dict.get("vr", None)
        self.adm: str = league_dict.get("adm", None)