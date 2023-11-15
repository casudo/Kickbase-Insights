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
        self.email = user_dict["email"]
        self.cover = user_dict["cover"]
        self.flags = user_dict["flags"]
        self.vemail = user_dict["vemail"]
        self.id = user_dict["id"]
        self.name = user_dict["name"]
        self.profile = user_dict["profile"]


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
        self.id = league_dict["id"]
        self.cpi = league_dict["cpi"]
        self.name = league_dict["name"]
        self.creator = league_dict["creator"]
        self.creatorId = league_dict["creatorId"]
        self.creation = league_dict["creation"]
        self.ai = league_dict["ai"]
        self.t = league_dict["t"]
        self.au = league_dict["au"]
        self.mu = league_dict["mu"]
        self.ap = league_dict["ap"]
        self.pub = league_dict["pub"]
        self.gm = league_dict["gm"]
        self.mpl = league_dict["mpl"]
        self.ci = league_dict["ci"]
        self.btlg = league_dict["btlg"]
        self.adm = league_dict["adm"]