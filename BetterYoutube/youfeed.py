"""
Aigis Internal plugin to monitor the RSS feeds of Youtube channels and send emails to subscribers.
"""
import asyncio
import signal
import json
import os
from threading import Event, Thread
from pprint import pprint as pp

import feedparser

import youtube_utils
import aigis  #pylint: disable=import-error

STATE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "config", "state.json"))
SUB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "config", "subscriptions.json"))

SHUTDOWN_EVENT = Event()

BASE_URL = "https://www.youtube.com/feeds/videos.xml?channel_id="


class OompaLoompa():
    """
    Class wrapper arounf the feed parsing logic to better contain the method of stopping it.

    DO NOT instanciate this class. Use static method fuckgoogle.main() if you are importing this,
    and fuckgoogle.BYT.stop() to kill it (or send SIGINT to program if you know how).
    """
    _continue = True  # Set to false to stop program
    with open(STATE_PATH, 'r+') as STATEFILE:
        ACTIVE_STATE = json.load(STATEFILE)
    SUBSCRIPTIONS = None

    def update_settings(self):
        """
        Pull changes to the SUBSCRIPTIONS file.
        """
        with open(SUB_PATH, 'r+') as SUBFILE:
            self.SUBSCRIPTIONS = json.load(SUBFILE)


    def stop(self):
        """
        Stop the watcher
        """
        self._continue = False


    async def parse_feed(self, subsettings):
        """
        Spawn and inspect RSS feed.

        :param str subsettings: Subscription settings dict.
        """
        feed = feedparser.parse(BASE_URL+subsettings["channel_id"])

        i = 0
        while feed.entries[i].id not in self.ACTIVE_STATE.get(feed.entries[i].author.lower(), ""):
            entry = feed.entries[i]
            helpfo = {
                "author": entry.author,
                "link": entry.link,
                "title": entry.title,
                "id": entry.id
            }
            # Queue an email send. Doesnt need to happen now /shrug
            asyncio.create_task(_send_email(helpfo, subsettings["subs"]))
            i += 1
        if i != 0:
            print("Updating active state")
            entry = feed.entries[0]
            self.ACTIVE_STATE[entry.author.lower()] = entry.id
            print("Active state updated")


    async def parse_subscriptions(self):
        """
        So long as we're not told to stop, keep pinging the RSS channels of all our subscriptions.
        If parsing the list of subscriptions iin under 30 seconds really becomes a problem, I'll need
        to put the sleeper in the individual feed parsers.
        """
        while self._continue:
            print("Updating local DB")
            await self._check_sub_state()
            print("Parsing subscriptions")
            sub_tasks = []
            for subscription in self.SUBSCRIPTIONS:
                print("Parsing %s" % subscription)
                sub_tasks.append(asyncio.create_task(self.parse_feed(self.SUBSCRIPTIONS[subscription])))
            # Wait for all subs to be processed.
            print("Waiting for all subs to be processed")
            await asyncio.gather(*sub_tasks)
            print("Done, queuing state save...")
            asyncio.create_task(save_state(self.ACTIVE_STATE, STATE_PATH))
            print("Sleeping for a bit...")
            await asyncio.sleep(30)


    async def _check_sub_state(self):
        """
        Update the ACTIVE_STATE based on new or removed entries in the SUBSCRIPTIONS file.
        This needs to be DB'd so it isnt dumb like this.
        """
        self.update_settings()
        for channel in list(self.ACTIVE_STATE):
            if channel not in self.SUBSCRIPTIONS:
                self.ACTIVE_STATE.pop(channel)
        for channel in self.SUBSCRIPTIONS:
            if channel not in self.ACTIVE_STATE:
                # We're adding a new channel, so we need to make sure we set a "latest video"
                await self._update_state(self.SUBSCRIPTIONS[channel]["channel_id"])


    async def _update_state(self, channel_id):
        """
        Fetch just the latest video of a channel and set the state to it. No notifications or anything.

        :param str channel_id: channel ID to update
        """
        feed = feedparser.parse(BASE_URL+channel_id)

        entry = feed.entries[0]
        # Don't send emails here.
        print("Updating active state")
        self.ACTIVE_STATE[entry.author.lower()] = entry.id
        await save_state(self.ACTIVE_STATE, STATE_PATH)


async def save_state(state, path):
    """
    Write one of the current states. Doing this async to the rest of the calls could cause mismatches
    if the client stops in edge cases, but we don't care enough.
    """
    with open(path, 'w+') as statefile:
        json.dump(state, statefile, indent=4)
    print("State saved")


async def _send_email(info, recipiants):
    """
    Send email to sub.
    """
    # TODO parse info into prettier format
    aigis.emailtools.simple_email(
        sender="zaltu@aigis.dev",
        recipiant=recipiants,
        subject="%s has uploaded a new video" % info["author"],
        message=info["title"] + "\n" + info["link"]
    )


def wait_thread():
    """
    Set CONTINUE when interrupt signal recieved.
    """
    print("Waiting...")
    SHUTDOWN_EVENT.wait()
    print("Shutdown request recieved")
    BYT.stop()


def launch():
    """
    Start up process and launch coroutine.
    """
    # Waste if running on AIGIS...
    Thread(target=wait_thread, daemon=True).start()
    asyncio.get_event_loop().run_until_complete(BYT.parse_subscriptions())


# Constant class instance.
BYT = OompaLoompa()
BYT.update_settings()

if __name__ == "__main__":
    # Insure any interrupt is handled smoothly.
    # Only needed when not running on AIGIS...
    signal.signal(signal.SIGINT, lambda a, b: SHUTDOWN_EVENT.set())
    launch()
