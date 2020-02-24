from ..cache import BaseCache
from tinyxbmc import hay


class HayCache(BaseCache):
    def __init__(self, directory, maxrecords=5000):
        self.hay = hay.stack(directory, "null", 0, maxrecords)

    def get(self, key):
        data = self.hay.find(key).data
        if data == {}:
            data = None
        return data

    def set(self, key, value):
        self.hay.throw(key, value)
        self.hay.snapshot()

    def delete(self, key):
        self.hay.lose(key)
        self.hay.snapshot()

    def close(self):
        self.hay.close()
