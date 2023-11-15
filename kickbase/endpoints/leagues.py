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
        ..next entry..
    ]}

    Everything that is stored directly under "items" is handled by the League_Feed class.
    Everything under "meta" is handled by this class.
    """

    bi: str = None # Buyers profile pic
    bid: str = None # Buyers id
    bn: str = None # Buyers name
    p: str = None # For how much the player was sold
    pfn: str = None # First name of the player
    pid: str = None # Player id
    pln: str = None # Last name of the player
    tid: str = None # Team id ?????

    def __init__(self, meta_dict: dict, type: int):
        if type == 12: # when a player is sold 
            self.bi = meta_dict["bi"]
            self.bid = meta_dict["bid"]
            self.bn = meta_dict["bn"]
            self.p = meta_dict["p"] 

        ### Standard attributes for all types    
        self.pfn = meta_dict["pfn"]
        self.pid = meta_dict["pid"]
        self.pln = meta_dict["pln"]
        self.tid = meta_dict["tid"]


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