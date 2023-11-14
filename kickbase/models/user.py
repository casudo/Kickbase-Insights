"""
Big giant test lmao
"""

class User:
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