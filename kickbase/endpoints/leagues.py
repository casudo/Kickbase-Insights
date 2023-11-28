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
        self.budget = league_user_info_dict["budget"]
        self.teamValue = league_user_info_dict["teamValue"]
        self.placement = league_user_info_dict["placement"]
        self.points = league_user_info_dict["points"]
        self.ttm = league_user_info_dict["ttm"]
        self.cmd = league_user_info_dict["cmd"]
        self.flags = league_user_info_dict["flags"]
        self.perms = league_user_info_dict["perms"]
        self.se = league_user_info_dict["se"]
        self.csid = league_user_info_dict["csid"]
        self.nt = league_user_info_dict["nt"]
        self.ntv = league_user_info_dict["ntv"]
        self.nb = league_user_info_dict["nb"]
        self.ga = league_user_info_dict["ga"]
        self.un = league_user_info_dict["un"]

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
    ### TODO: Add same for sold (Type 2)
    # si
    # sn
    # sid
    ### TODO: Add same for final matchday points (Type 8)
    # day
    # a
    # t
    # m
    ### Meta attributes for buy feed entry (Type 12)
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
        if type != 8: 
            if type == 12: # when a player is sold 
                if "bi" in meta_dict:
                    self.bi = meta_dict["bi"] # only set profile pic if it exists
                self.bid = meta_dict["bid"]
                self.bn = meta_dict["bn"]
                self.p = meta_dict["p"] 
                if "pi" in meta_dict: 
                    self.pi = meta_dict["pi"] # not always set

            ### TODO: Add same for sold (Type 2)

            ### Standard attributes for all types    
            self.pfn = meta_dict["pfn"]
            self.pid = meta_dict["pid"]
            self.pln = meta_dict["pln"]
            self.tid = meta_dict["tid"]
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
    age: int = None # How long ago the event happened (in seconds)
    comments: int = None
    date: str = None
    id: str = None
    meta: dict = None
    seasonId: int = None
    source: int = None
    type: int = None

    def __init__(self, league_feed_dict: dict):
        self.age = league_feed_dict["age"]
        self.comments = league_feed_dict["comments"]
        self.date = league_feed_dict["date"]
        self.id = league_feed_dict["id"]
        self.seasonId = league_feed_dict["seasonId"]
        self.source = league_feed_dict["source"]
        self.type = league_feed_dict["type"]

        ### Create a new object with all its attributes for everything stored in the meta dict
        self.meta = Meta(league_feed_dict["meta"], self.type)

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
        self.id = market_players_dict["id"]
        self.teamId = market_players_dict["teamId"]
        if "userId" in market_players_dict:
            self.userId = market_players_dict["userId"]
            self.username = market_players_dict["username"]
        if "userProfile" in market_players_dict:
            self.userProfile = market_players_dict["userProfile"]
        self.firstName = market_players_dict["firstName"]
        self.lastName = market_players_dict["lastName"]
        if "profile" in market_players_dict: 
            self.profile = market_players_dict["profile"]
        self.status = market_players_dict["status"]
        self.position = market_players_dict["position"]
        self.number = market_players_dict["number"]
        self.totalPoints = market_players_dict["totalPoints"]
        self.averagePoints = market_players_dict["averagePoints"]
        self.marketValue = market_players_dict["marketValue"]
        self.price = market_players_dict["price"]
        self.date = market_players_dict["date"]
        self.expiry = market_players_dict["expiry"]
        if "offers" in market_players_dict:
            self.offers = market_players_dict["offers"]
        self.lus = market_players_dict["lus"]
        self.marketValueTrend = market_players_dict["marketValueTrend"]