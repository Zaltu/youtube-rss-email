"""
Some extra utilities for handling Youtube data.
"""
import os
import requests

SECRET_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "config", "youtube.secret"))
with open(SECRET_PATH, 'r') as SECRETFILE:
    SECRET = SECRETFILE.readline()

BASE_URL = "https://www.googleapis.com/youtube/v3/channels?"
DEFAULT_SETTINGS = {
    "part": "brandingSettings",
    "id": "UC-lHJZR3Gqxm24_Vd_AJ5Yw",
    "key": SECRET
}


def _buildUArgl(overwrite={}):  #pylint: disable=dangerous-default-value
    """
    Build a query URL, potentially overwriting default settings if necessary.

    :param dict overwrite: custom settings added for this query

    :return: ready-to-fire URL
    :rtype: str
    """
    url = BASE_URL
    for key, value in overwrite.items():
        url += "&" + key + "=" + value
    for key, value in DEFAULT_SETTINGS.items():
        if key not in overwrite:
            url += "&" + key + "=" + value
    return url


def _fetch_youtube_info(**kwargs):
    """
    Make a general call to the Youtube API v3

    :param kwargs: any overwritten or extra arguments to add to the query

    :return: request result
    :rtype: dict
    """
    url = _buildUArgl(kwargs)
    res = requests.get(url)
    try:
        res.raise_for_status()
    except requests.HTTPError:
        return res.status_code
    return res.json()


def get_channel_name(channel_id):
    """
    Get the public channel name for a given channel ID (may not be unique).

    :param str channel_id: channel ID to search

    :return: Channel name associated to ID, or None if channel cannot be found.
    :rtype: str | None
    """
    full = _fetch_youtube_info(id=channel_id)
    try:
        return full["items"][0]["brandingSettings"]["channel"]["title"]
    except KeyError:
        print(full)
        return None
