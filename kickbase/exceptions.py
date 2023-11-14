"""
my cool exceptions
"""

class KickbaseException(Exception):
    """Base class for exceptions in this module."""
    pass

class LoginException(Exception):
    """Exception raised for errors in the login process."""
    pass

class NotificatonException(Exception):
    """Exception raised for errors in the notification process."""
    pass