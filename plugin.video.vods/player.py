'''
Created on Sep 30, 2025

@author: boogie
'''
from tinyxbmc import extension
from tinyxbmc import addon as tinyaddon

import traceback

EP_LINKPLAYER = "vodslinkplayer"
EP_ADDONPLAYER = "vodsaddonplayer"


class Players:
    def __init__(self, addon, link, log=None):
        self.log = log or tinyaddon.log
        self.players = []
        # find link players
        if link:
            for player in extension.getplugins(EP_LINKPLAYER):
                self.log("Found link player: %s" % repr(player))
                self.players.append([player, None])
        # find addon players
        if addon:
            for player in extension.getplugins(EP_ADDONPLAYER):
                self.log("Found addon player: %s" % repr(player))
                self.players.append([player, None])
        self.log("Found total number of players: %d" % (len(self.players)))

    def target(self, playerins):
        return playerins._tinyxbmc.get("module", repr(playerins))

    def list(self):
        for prio in range(len(self.players)):
            player, playerins = self.players[prio]
            if not playerins:
                try:
                    playerins = player(self)
                    self.log("Instantiated player: %s" % self.target(playerins))
                except Exception:
                    self.log("Error instantiating player: %s" % repr(player))
                    self.log(traceback.format_exc())
                    continue
                self.players[prio][1] = playerins
            yield playerins
