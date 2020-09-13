"""
Fix Youtube's shitty decision making.
"""
import asyncio
import signal
import json
import os
from threading import Event, Thread
from pprint import pprint as pp

import feedparser

#import stmp handler TODO

STATE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "config", "state.json"))
with open(STATE_PATH, 'r+') as STATEFILE:
    ACTIVE_STATE = json.load(STATEFILE)

SHUTDOWN_EVENT = Event()

BASE_URL = "https://www.youtube.com/feeds/videos.xml?channel_id="

SUBSCRIPTIONS = {
    "pewdiepie": {
        "channel_id": "UC-lHJZR3Gqxm24_Vd_AJ5Yw",
        "subs": [
            "swwouf@hotmail.com"
        ]
    }
}


class BetterYoutube():
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


    async def parse_feed(self, subsettings):
        """
        Spawn and inspect RSS feed.

        :param str subsettings: Subscription settings dict.
        """
        feed = feedparser.parse(BASE_URL+subsettings["channel_id"])

        i = 0
        #print("Current ID: %s" % feed.entries[i].id)
        #print("Matching to ID %s" % ACTIVE_STATE.get(feed.entries[i].author.lower(), ""))
        while feed.entries[i].id not in ACTIVE_STATE.get(feed.entries[i].author.lower(), ""):
            entry = feed.entries[i]
            helpfo = {
                "author": entry.author,
                "link": entry.link,
                "title": entry.title
            }
            pp(helpfo)  # TODO send email
            i += 1
        if i != 0:
            print("Updating active state")
            entry = feed.entries[0]
            ACTIVE_STATE.set_default(entry.author.lower(), entry.id)


    async def parse_subscriptions(self):
        """
        So long as we're not told to stop, keep pinging the RSS channels of all our subscriptions.
        If parsing the list of subscriptions iin under 30 seconds really becomes a problem, I'll need
        to put the sleeper in the individual feed parsers.
        """
        while self._continue:
            for subscription in SUBSCRIPTIONS:
                asyncio.create_task(self.parse_feed(SUBSCRIPTIONS[subscription]))
            asyncio.create_task(save_state())
            await asyncio.sleep(30)


async def save_state():
    """
    Write the currently active state. Doing this async to the rest of the calls could cause mismatches
    if the client stops in edge cases, but we don't care enough.
    """
    with open(STATE_PATH, 'w+') as statefile:
        json.dump(ACTIVE_STATE, statefile, indent=4)



def wait_thread():
    """
    Set CONTINUE when interrupt signal recieved.
    """
    print("Waiting...")
    SHUTDOWN_EVENT.wait()
    print("Shutdown request recieved")  # Test on a real OS
    BYT.stop()


def launch():
    """
    Start up process and launch coroutine.
    """
    # Waste if running on AIGIS...
    Thread(target=wait_thread, daemon=True).start()
    asyncio.get_event_loop().run_until_complete(BYT.parse_subscriptions())


# Constant class instance.
BYT = BetterYoutube()

if __name__ == "__main__":
    # Insure any interrupt is handled smoothly.
    # Only needed when not running on AIGIS...
    signal.signal(signal.SIGINT, lambda a, b: SHUTDOWN_EVENT.set())
    launch()
