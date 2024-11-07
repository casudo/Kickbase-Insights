"""
### This file contains all models for the leagues endpoint, regardless of the API version.

#### Endpoint:
`/vX/leagues/...`
"""

class League_Info:
    """
    ### Create an object for a league with all its attributes.

    Used for endpoint URL:
    `/leagues/selection` -> get all leagues the user is in
    """
    def __init__(self, league_dict: dict):
        self.id: str = league_dict.get("i", None)  ### League ID
        self.name: str = league_dict.get("n", None)  ### League name
        self.cpi: str = league_dict.get("cpi", None)
        self.b: int = league_dict.get("b", None)  ### Budget of player
        self.un: int = league_dict.get("un", None)
        self.f: str = league_dict.get("f", None) ### League Image
        self.lpc: int = league_dict.get("lpc", None)
        self.bs: int = league_dict.get("bs", None)
        self.vr: int = league_dict.get("vr", None)
        self.adm: bool = league_dict.get("adm", None) ### Admin
        self.pl: int = league_dict.get("pl", None)
        self.tv: int = league_dict.get("tv", None) ### Team value of player
        # self.creator: str = league_dict.get("creator", None)  ### League creator's username
        # self.creatorId: str = league_dict.get("creatorId", None)  ### League creator's ID
        # self.creation: str = league_dict.get("creation", None)  ### League creation date
        # self.ai: str = league_dict.get("ai", None)
        # self.t: str = league_dict.get("t", None)
        # self.au: str = league_dict.get("au", None)
        # self.mu: str = league_dict.get("mu", None)
        # self.ap: str = league_dict.get("ap", None)  ### Not always present
        # self.pub: str = league_dict.get("pub", None)
        # self.gm: str = league_dict.get("gm", None)
        # self.mpl: str = league_dict.get("mpl", None)
        # self.ci: str = league_dict.get("ci", None)
        # self.btlg: str = league_dict.get("btlg", None)  ### Not always present
        # self.vr: str = league_dict.get("vr", None)


class League_User_Info:
    """
    ### Create an object for the league user info with all its attributes.

    Used for endpoint URL:
    `/leagues/{league_id}/me` -> get user's stats in the given league
    """
    def __init__(self, league_user_info_dict: dict):
        self.budget: float = league_user_info_dict.get("budget", None)
        self.teamValue: float = league_user_info_dict.get("teamValue", None)
        self.placement: int = league_user_info_dict.get("placement", None)
        self.points: int = league_user_info_dict.get("points", None)
        self.ttm: int = league_user_info_dict.get("ttm", None)
        self.cmd: int = league_user_info_dict.get("cmd", None)
        self.flags: int = league_user_info_dict.get("flags", None)
        self.perms: list = league_user_info_dict.get("perms", None)
        self.se: bool = league_user_info_dict.get("se", None)
        self.csid: int = league_user_info_dict.get("csid", None)
        self.nt: bool = league_user_info_dict.get("nt", None)
        self.ntv: float = league_user_info_dict.get("ntv", None)
        self.nb: float = league_user_info_dict.get("nb", None)
        self.ga: bool = league_user_info_dict.get("ga", None)
        self.un: int = league_user_info_dict.get("un", None)

### ===============================================================================
### League Feed stuff

class Meta:
    """
    ### Create an object for the meta dict in the league feed with all its attributes.

    The JSON response for the feed entries looks like this:
    ```json
    {items: [
        {
            "age": 0,
            "comments": 0,
            "date": "2021-07-18T16:00:00.000Z",
            "id": "60f3d4c0e4b0c6b0d5b5f4d0",
            "meta": {
                "bi": "https://cdn.kickbase.com/images/avatars/0.png",
                "bid": "60f3d4c0e4b0c6b0d5b5f4d0",
                "bn": "Max Mustermann",
                "p": "1000000",
                "pfn": "Max",
                "pid": "60f3d4c0e4b0c6b0d5b5f4d0",
                "pln": "Mustermann",
                "tid": "60f3d4c0e4b0c6b0d5b5f4d0"
            },
            "seasonId": 20,
            "source": 12,
            "type": 12
        },
        { ... },
    ]}

    Everything that is stored directly under "items" is handled by the League_Feed class.
    Everything under "meta" is handled by this class.
    """
    def __init__(self, meta_dict: dict, type: int):
        ### Meta attributes for Type 2 SPECIFIC
        self.si: str = meta_dict.get("si", None)  # Sellers profile pic
        self.sn: str = meta_dict.get("sn", None)  # Sellers name
        self.sid: str = meta_dict.get("sid", None)  # Sellers id
        ### Meta attributes for buy feed entry (Type 12) AND Type 2 IF user sold to user
        self.bi: str = meta_dict.get("bi", None)  # Buyers profile pic
        self.bid: str = meta_dict.get("bid", None)  # Buyers id
        self.bn: str = meta_dict.get("bn", None)  # Buyers name
        self.p: str = meta_dict.get("p", None)  # For how much the player was sold
        ### Standard attributes for all types (except Type 8)
        self.pid: str = meta_dict.get("pid", None)  # Player id
        self.tid: str = meta_dict.get("tid", None)  # Team id
        self.pfn: str = meta_dict.get("pfn", None)  # First name of the player
        self.pln: str = meta_dict.get("pln", None)  # Last name of the player
        self.pi: str = meta_dict.get("pi", None)  # Player image

        ### First of all, check the type of the feed entry
        if type != 8:  # Not a final matchday points entry
            ### Type 2: User sold to Kickbase AND User sold to User
            if type == 2 and not "bn" in meta_dict:  # User sold to Kickbase
                self.sid = meta_dict.get("sid", None)
                self.sn = meta_dict.get("sn", None)
                self.si = meta_dict.get("si", None)
                self.p = meta_dict.get("p", None)
                self.pi = meta_dict.get("pi", None)
            elif type == 2 and "bn" in meta_dict:  # User sold to User
                self.sid = meta_dict.get("sid", None)
                self.sn = meta_dict.get("sn", None)
                self.si = meta_dict.get("si", None)
                self.bid = meta_dict.get("bid", None)
                self.bn = meta_dict.get("bn", None)
                self.bi = meta_dict.get("bi", None)
                self.p = meta_dict.get("p", None)
                self.pi = meta_dict.get("pi", None)

            if type == 12:  # User bought from Kickbase
                self.bid = meta_dict.get("bid", None)
                self.bn = meta_dict.get("bn", None)
                self.bi = meta_dict.get("bi", None)
                self.p = meta_dict.get("p", None)
                self.pi = meta_dict.get("pi", None)
        else:  ### TODO: Necessary?
            print("Skipping this feed entry because it is a final matchday points entry.")

class League_Feed:
    """
    ### Create an object for an entry in the league feed with all its attributes.

    Used for endpoint URL:
    `/leagues/{league_id}/feed?start=0` -> get the league feed

    Example to get the players first name:
    ### Get the whole feed
    ```python
    league_feed = leagues.league_feed(token, league[0].id)
    ```

    ### Loop through all entries and print the players first name
    ```python
    for feed_entry in league_feed:
        print(f"First name: {feed_entry.meta.pfn}
    ```
    """
    def __init__(self, league_feed_dict: dict):
        self.id: str = league_feed_dict.get("id", None)
        self.comments: int = league_feed_dict.get("comments", None)
        self.date: str = league_feed_dict.get("date", None)
        self.age: int = league_feed_dict.get("age", None)  # How long ago the event happened (in seconds)
        self.type: int = league_feed_dict.get("type", None)
        self.source: int = league_feed_dict.get("source", None)
        ### Create a new object with all its attributes for everything stored in the meta dict
        self.meta = Meta(league_feed_dict["meta"], self.type)
        self.seasonId: int = league_feed_dict.get("seasonId", None)


### End of League Feed stuff
### ===============================================================================


class Market_Players:
    """
    ### Create an object for a player on the market with all its attributes.
    
    Used for endpoint URL:
    `/leagues/{league_id}/market` -> get the whole market
    """
    def __init__(self, market_players_dict: dict):
        self.id: str = market_players_dict.get("id", None)
        self.teamId: str = market_players_dict.get("teamId", None)
        self.userId: str = market_players_dict.get("userId", None)  # Set if player is listed by a user
        self.userProfile: str = market_players_dict.get("userProfile", None)  # OPTIONAL: Set if player is listed by a user
        self.username: str = market_players_dict.get("username", None)  # Set if player is listed by a user
        self.firstName: str = market_players_dict.get("firstName", None)
        self.lastName: str = market_players_dict.get("lastName", None)
        self.profile: str = market_players_dict.get("profile", None)  # Somehow not always present e.g. Kevin Müller
        self.status: int = market_players_dict.get("status", None)
        self.position: int = market_players_dict.get("position", None)
        self.number: int = market_players_dict.get("number", None)
        self.totalPoints: int = market_players_dict.get("totalPoints", None)
        self.averagePoints: int = market_players_dict.get("averagePoints", None)
        self.marketValue: float = market_players_dict.get("marketValue", None)
        self.price: float = market_players_dict.get("price", None)
        self.date: str = market_players_dict.get("date", None)
        self.expiry: str = market_players_dict.get("expiry", None)
        self.offers: list = market_players_dict.get("offers", None)
        self.lus: int = market_players_dict.get("lus", None)
        self.marketValueTrend: int = market_players_dict.get("marketValueTrend", None)