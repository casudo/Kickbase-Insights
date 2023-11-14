"""
Big giant test lmao
"""

class Leagues:
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

    def __init__(self, leagues_dict: dict):
        self.id = leagues_dict["id"]
        self.cpi = leagues_dict["cpi"]
        self.name = leagues_dict["name"]
        self.creator = leagues_dict["creator"]
        self.creatorId = leagues_dict["creatorId"]
        self.creation = leagues_dict["creation"]
        self.ai = leagues_dict["ai"]
        self.t = leagues_dict["t"]
        self.au = leagues_dict["au"]
        self.mu = leagues_dict["mu"]
        self.ap = leagues_dict["ap"]
        self.pub = leagues_dict["pub"]
        self.gm = leagues_dict["gm"]
        self.mpl = leagues_dict["mpl"]
        self.ci = leagues_dict["ci"]
        self.btlg = leagues_dict["btlg"]
        self.adm = leagues_dict["adm"]