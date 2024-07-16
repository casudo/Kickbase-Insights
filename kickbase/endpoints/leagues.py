"""
### This file contains all models for the leagues endpoint.

Endpoint:
`/leagues/{league_id}/...`
"""

class League_User_Info:
    """
    ### Create an object for the league user info with all its attributes.

    Used for endpoint URL:
    `/leagues/{league_id}/me` -> get user's stats in the given league
    """
    budget: float = None
    teamValue: float = None
    placement: int = None
    points: int = None
    ttm: int = None
    cmd: int = None
    flags: int = None
    perms: list = None
    se: bool = None
    csid: int = None
    nt: bool = None
    ntv: float = None
    nb: float = None
    ga: bool = None
    un: int = None

    def __init__(self, league_user_info_dict: dict):
        self.budget = league_user_info_dict.get("budget", None)
        self.teamValue = league_user_info_dict.get("teamValue", None)
        self.placement = league_user_info_dict.get("placement", None)
        self.points = league_user_info_dict.get("points", None)
        self.ttm = league_user_info_dict.get("ttm", None)
        self.cmd = league_user_info_dict.get("cmd", None)
        self.flags = league_user_info_dict.get("flags", None)
        self.perms = league_user_info_dict.get("perms", None)
        self.se = league_user_info_dict.get("se", None)
        self.csid = league_user_info_dict.get("csid", None)
        self.nt = league_user_info_dict.get("nt", None)
        self.ntv = league_user_info_dict.get("ntv", None)
        self.nb = league_user_info_dict.get("nb", None)
        self.ga = league_user_info_dict.get("ga", None)
        self.un = league_user_info_dict.get("un", None)

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
    ### Meta attributes for Type 2 SPECIFIC
    si: str = None # Sellers profile pic
    sn: str = None # Sellers name
    sid: str = None # Sellers id
    ### TODO: Add same for final matchday points (Type 8)
    # day
    # a
    # t
    # m
    ### Meta attributes for buy feed entry (Type 12) AND Type 2 IF user sold to user
    bi: str = None # Buyers profile pic
    bid: str = None # Buyers id
    bn: str = None # Buyers name
    p: str = None # For how much the player was sold
    ### Standard attributes for all types (except Type 8)
    pid: str = None # Player id
    tid: str = None # Team id
    pfn: str = None # First name of the player
    pln: str = None # Last name of the player
    pi: str = None # Player image

    def __init__(self, meta_dict: dict, type: int):
        ### First of all, check the type of the feed entry
        if type != 8: # Not a final matchday points entry
            ### Type 2: User sold to Kickbase AND User sold to User
            if type == 2 and not "bn" in meta_dict: # User sold to Kickbase
                self.sid = meta_dict.get("sid", None)
                self.sn = meta_dict.get("sn", None)
                self.si = meta_dict.get("si", None)
                self.p = meta_dict.get("p", None)  
                self.pi = meta_dict.get("pi", None)         
            elif type == 2 and "bn" in meta_dict: # User sold to User
                self.sid = meta_dict["sid"]
                self.sn = meta_dict["sn"]
                self.sid = meta_dict.get("sid", None)
                self.sn = meta_dict.get("sn", None)
                self.si = meta_dict.get("si", None)
                self.bid = meta_dict.get("bid", None)
                self.bn = meta_dict.get("bn", None)
                self.bi = meta_dict.get("bi", None)
                self.p = meta_dict.get("p", None) 
                self.pi = meta_dict.get("pi", None)                        

            if type == 12: # User bought from Kickbase
                self.bid = meta_dict.get("bid", None)
                self.bn = meta_dict.get("bn", None)
                self.bi = meta_dict.get("bi", None)
                self.p = meta_dict.get("p", None) 
                self.pi = meta_dict.get("pi", None)

            ### Standard attributes for all types    
            self.pid = meta_dict.get("pid", None)
            self.tid = meta_dict.get("tid", None)
            self.pfn = meta_dict.get("pfn", None)
            self.pln = meta_dict.get("pln", None)
        else: ### TODO: Necessary?
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
    id: str = None
    comments: int = None
    date: str = None
    age: int = None # How long ago the event happened (in seconds)
    type: int = None
    source: int = None
    meta: dict = None
    seasonId: int = None

    def __init__(self, league_feed_dict: dict):
        self.id = league_feed_dict.get("id", None)
        self.comments = league_feed_dict.get("comments", None)
        self.date = league_feed_dict.get("date", None)
        self.age = league_feed_dict.get("age", None)
        self.type = league_feed_dict.get("type", None)
        self.source = league_feed_dict.get("source", None)
        ### Create a new object with all its attributes for everything stored in the meta dict
        self.meta = Meta(league_feed_dict["meta"], self.type)
        self.seasonId = league_feed_dict.get("seasonId", None)


### End of League Feed stuff
### ===============================================================================


class Market_Players:
    """
    ### Create an object for a player on the market with all its attributes.
    
    Used for endpoint URL:
    `/leagues/{league_id}/market` -> get the whole market
    """
    id: str = None
    teamId: str = None
    userId: str = None # Set if player is listed by a user
    userProfile: str = None # OPTIONAL: Set if player is listed by a user
    username: str = None # Set if player is listed by a user
    firstName: str = None
    lastName: str = None
    profile: str = None # Somehow not always present e.g. Kevin Müller
    status: int = None
    position: int = None
    number: int = None
    totalPoints: int = None
    averagePoints: int = None
    marketValue: float = None
    price: float = None
    date: str = None
    expiry: str = None
    offers: list = None
    lus: int = None
    marketValueTrend: int = None

    def __init__(self, market_players_dict: dict):
        self.id = market_players_dict.get("id", None)
        self.teamId = market_players_dict.get("teamId", None)
        self.userId = market_players_dict.get("userId", None)
        self.username = market_players_dict.get("username", None)
        self.userProfile = market_players_dict.get("userProfile", None)
        self.firstName = market_players_dict.get("firstName", None)
        self.lastName = market_players_dict.get("lastName", None)
        self.profile = market_players_dict.get("profile", None)
        self.status = market_players_dict.get("status", None)
        self.position = market_players_dict.get("position", None)
        self.number = market_players_dict.get("number", None)
        self.totalPoints = market_players_dict.get("totalPoints", None)
        self.averagePoints = market_players_dict.get("averagePoints", None)
        self.marketValue = market_players_dict.get("marketValue", None)
        self.price = market_players_dict.get("price", None)
        self.date = market_players_dict.get("date", None)
        self.expiry = market_players_dict.get("expiry", None)
        self.offers = market_players_dict.get("offers", None)
        self.lus = market_players_dict.get("lus", None)
        self.marketValueTrend = market_players_dict.get("marketValueTrend", None)