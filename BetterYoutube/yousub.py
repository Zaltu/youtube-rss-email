"""
Aigis Core plugin to set and update subscriptions to Youtube channels
"""
import json
import os
from pprint import pprint as pp

import youtube_utils  #pylint: disable=import-error

SUB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "config", "subscriptions.json"))

with open(SUB_PATH, 'r+') as SUBFILE:
    SUBSCRIPTIONS = json.load(SUBFILE)

BASE_URL = "https://www.youtube.com/feeds/videos.xml?channel_id="


class SubToPewdiepie():
    """
    Class wrapper arounf the feed parsing logic to better contain the method of stopping it.

    DO NOT instanciate this class. Use static method fuckgoogle.main() if you are importing this,
    and fuckgoogle.BYT.stop() to kill it (or send SIGINT to program if you know how).
    """
    _continue = True  # Set to false to stop program

    def stop(self):
        """
        Stop the watcher
        """
        self._continue = False


    def subscribe(self, channel_id, email):
        """
        Subscribe a user to a channel. Also schedules a task to write the updated config to disk.

        :param str channel_id: the channel ID to subscribe (sometimes takes channel name, don't tell anyone)
        :param str email: the email address to subscribe with

        :return: if the operation was successful.
        :rtype: bool
        """
        delta = _add_sub(channel_id, email)
        if delta:
            save_state(SUBSCRIPTIONS, SUB_PATH)
        return delta


    def unsubscribe(self, channel, email):
        """
        Unsubscribe a user from a channel.

        :param str channel: The channel *name* to unsubscribe from
        :param str email: the user to unsubscribe

        :return: if the operation was successful
        :rtype: bool
        """
        if channel in SUBSCRIPTIONS and email in SUBSCRIPTIONS.get(channel, {}).get("subs", []):
            SUBSCRIPTIONS[channel]["subs"].remove(email)
            # No more subs, remove the entry completely
            if len(SUBSCRIPTIONS[channel]["subs"]) == 0:
                _kill_channel(channel)
            save_state(SUBSCRIPTIONS, SUB_PATH)
            return True
        # Could be the user typoed the channel name too...
        return False


def save_state(state, path):
    """
    Write one of the current states.
    if the client stops in edge cases, but we don't care enough.
    """
    with open(path, 'w+') as statefile:
        json.dump(state, statefile, indent=4)


def _add_sub(channel_id, email):
    """
    Add a subscription to channel for email.

    :param str channel_id: the channel ID to subscribe (sometimes takes channel name, don't tell anyone)
    :param str email: the email address to subscribe with

    :return: if the operation was successful.
    :rtype: bool
    """
    # Just in case we already have the channel. It's easier for the user this way.
    if channel_id.lower() in SUBSCRIPTIONS and email not in SUBSCRIPTIONS[channel_id.lower()]["subs"]:
        SUBSCRIPTIONS[channel_id.lower()]["subs"].append(email)
        return True
    # If the user is already subbed
    if channel_id.lower() in SUBSCRIPTIONS and email in SUBSCRIPTIONS[channel_id.lower()]["subs"]:
        return False
    cname = youtube_utils.get_channel_name(channel_id)
    if not cname:
        # Someone probably gave a channel "name" we don't have the ID for yet (or a bad ID)
        return False
    cname = cname.lower()
    if cname in SUBSCRIPTIONS and email not in SUBSCRIPTIONS[cname]["subs"]:
        SUBSCRIPTIONS[cname]["subs"].append(email)
        return True
    if cname not in SUBSCRIPTIONS:
        SUBSCRIPTIONS[cname] = {
            "channel_id": channel_id,
            "subs": [email]
        }
        return True
    # Unknown issue :thinking:
    return False

def _kill_channel(channel_name):
    """
    Remove a channel from the SUBSCRIPTIONS dict.
    No check is made to validate the channel is in there, that should be done upstream.
    ACTIVE_STATE IS NOT UPDATED. "DB" conflict means it needs to only be updated by the daemon.

    :param str channel_name: name of channel to remove
    """
    SUBSCRIPTIONS.pop(channel_name)
    save_state(SUBSCRIPTIONS, SUB_PATH)
