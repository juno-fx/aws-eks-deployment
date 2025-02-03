SESSION = None
PROFILE = None


def get_session():
    global SESSION
    return SESSION


def set_session(session):
    global SESSION
    SESSION = session


def get_profile():
    global PROFILE
    return PROFILE


def set_profile(profile):
    global PROFILE
    PROFILE = profile
