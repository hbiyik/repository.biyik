import sys

sys.argv = ["plugin://service.subtitles.turkcealtyazi", "1", "?action=search&preflang=en&langs=en%2Ctr"]

import service
from sublib import utils

class testclass(service.turkcealtyazi):
    def oninit(self):
        self.item.title = "Matrix"
        self.item.imdb = "tt0133093"

client = testclass(utils.mozilla)
for sub in client._subs:
    print sub