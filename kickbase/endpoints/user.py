"""
### This file contains all models for the `/user/...` endpoint.

Endpoint:
/user/...
"""

class User:
    """
    ### This class will create on object with all user information given upon logging in.

    Used for endpoint URL:
    `/user/login` -> get all user data
    """
    email: str = None
    cover: str = None
    flags: str = None
    vemail: str = None
    # perms
    id: str = None
    name: str = None
    profile: str = None

    def __init__(self, user_dict: dict):
        self.email = user_dict.get("email", None)
        self.cover = user_dict.get("cover", None)
        self.flags = user_dict.get("flags", None)
        self.vemail = user_dict.get("vemail", None)
        self.id = user_dict.get("id", None)
        self.name = user_dict.get("name", None)
        self.profile = user_dict.get("profile", None)


class League:
    """
    ### Create an object for a league with all its attributes.

    Used for endpoint URL:
    `/user/login` -> get all leagues the user is in
    """
    id: str = None
    cpi: str = None
    name: str = None
    creator: str = None
    creatorId: str = None
    creation: str = None
    ai: str = None
    t: str = None
    au: str = None
    mu: str = None
    ap: str = None
    pub: str = None
    gm: str = None
    mpl: str = None
    ci: str = None
    btlg: str = None
    adm: str = None

    def __init__(self, league_dict: dict):
        self.id = league_dict.get("id", None)
        self.cpi = league_dict.get("cpi", None)
        self.name = league_dict.get("name", None)
        self.creator = league_dict.get("creator", None)
        self.creatorId = league_dict.get("creatorId", None)
        self.creation = league_dict.get("creation", None)
        self.ai = league_dict.get("ai", None)
        self.t = league_dict.get("t", None)
        self.au = league_dict.get("au", None)
        self.mu = league_dict.get("mu", None)
        self.ap = league_dict.get("ap", None)
        self.pub = league_dict.get("pub", None)
        self.gm = league_dict.get("gm", None)
        self.mpl = league_dict.get("mpl", None)
        self.ci = league_dict.get("ci", None)
        self.btlg = league_dict.get("btlg", None)
        self.vr = league_dict.get("vr", None)
        self.adm = league_dict.get("adm", None)