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