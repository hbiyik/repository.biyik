# -*- coding: utf-8 -*-
'''
    Author    : Huseyin BIYIK <husenbiyik at hotmail>
    Year      : 2016
    License   : GPL

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''


import json
import os
import time
import zlib
try:
    import cPickle as pickle
except ImportError:
    import pickle as pickle

import sqlite3

_debug = False


def _null(data, *args, **kwargs):
    return data


class needle():
    def __init__(self, id=None, data=None, timestamp=None, serial=None, compress=0):
        self.compress = compress
        self.id = id
        self.data = data
        self.timestamp = timestamp
        if serial is None:
            self.serial = "p_%s" % pickle.HIGHEST_PROTOCOL
        else:
            self.serial = serial
        self.hash = None

    def __repr__(self):
        return repr({
                "hash": self.hash,
                "id": self.id,
                "data": self.data,
                "timestamp": self.timestamp,
                "serial": self.serial,
                "compress": self.compress
                })

    def dohash(self, ser=None):
        if self.id:
            self.hash = hash(self.id)
        elif ser:
            self.hash = hash(ser)

    def deser(self, serdata):
        self.dohash(str(serdata))
        if self.compress:
            serdata = zlib.decompress(serdata)
        if self.serial.startswith("p_"):
            self.data = pickle.loads(serdata)
        elif self.serial == "json":
            self.data = json.loads(serdata)
        elif self.serial == "null":
            self.data = str(serdata)

    def ser(self):
        if self.compress:
            comp = zlib.compress
        else:
            comp = _null
        if self.serial.startswith("p_"):
            protocol = int(self.serial.split("_")[1])
            serdata = buffer(comp(pickle.dumps(self.data, protocol)))
        elif self.serial == "json":
            serdata = sqlite3.Binary(comp(json.dumps(self.data)))
        elif self.serial == "null":
            serdata = sqlite3.Binary(comp(self.data))
        self.dohash(serdata)
        return serdata


class stack(object):
    def __init__(self, path, serial=None, compress=1, maxrows=5000, write=True, common=False):
        self.write = write
        self.compress = compress
        self.maxrows = maxrows
        self.path = path
        if type(common) == type(True):
            from tinyxbmc import addon
            if common:
                bpath = addon.get_commondir()
            else:
                bpath = addon.get_addondir()
        else:
            bpath = common
        path = os.path.join(bpath, path)
        if not os.path.exists(path):
            os.makedirs(path)
        path = os.path.join(path, "haystack.db")
        self._open_db(path)
        if not self._check_db():
            self._create_table()
        self.serial = serial
        self.__closed = False

    @property
    def isclosed(self):
        return self.__closed

    def __enter__(self):
        self.ts = time.time()
        return self

    def __exit__(self, typ, value, traceback):
        self.close()
        if _debug:
            optime = (time.time() - self.ts) * 1000
            print "DB: %s, Operation Time (ms): %s " % (self.path, optime)

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def _check_db(self):
        columns = [u"hash", u"id", u"data", u"timestamp", u"ser", u"compress"]
        self.cur.execute("""PRAGMA table_info(needles)""")
        k = 0
        for row in self.cur:
            if not row[1] == columns[k]:
                break
            k += 1
        return k == 6

    def _create_table(self):
        if _debug:
            print "DB: %s, Created a new haystack" % self.path
        self.cur.executescript("""
                        PRAGMA AUTO_VACUUM = FULL;
                        PRAGMA JOURNAL_MODE = MEMORY;
                        PRAGMA SYNCHRONOUS = OFF;
                        PRAGMA LOCKING_MODE = UNLOCKED;
                        DROP TABLE IF EXISTS 'needles';
                        CREATE TABLE 'needles' (
                            'hash'    INTEGER NOT NULL UNIQUE,
                            'id'    TEXT,
                            'data'    BLOB,
                            'timestamp'    TEXT,
                            'ser'    TEXT,
                            'compress'    INTEGER NOT NULL,
                            PRIMARY KEY(hash)
                        );
                        CREATE INDEX 'hash_index' ON 'needles' ('hash' ASC);
                        """)

    def _open_db(self, path):
        if _debug:
            print "DB: %s, opened at %s" % (self.path, path)
        self.conn = sqlite3.connect(path)
        self.cur = self.conn.cursor()
        self.cur.executescript("""
                               PRAGMA JOURNAL_MODE = MEMORY;
                               PRAGMA SYNCHRONOUS = OFF;
                               PRAGMA LOCKING_MODE = UNLOCKED;""")

    def _close_db(self):
        if self.write:
            self.snapshot()
        self.cur.close()
        self.conn.close()
        if _debug:
            print "DB: %s, saved and closed" % self.path

    def _select_row(self, n, since=0, do=True):
        if since > 0:
            gap = time.time() - since * 60 * 60
        else:
            gap = 0
        self.cur.execute("""SELECT * FROM needles WHERE hash=? and timestamp >= ? LIMIT 1;""",
                         (n.hash, gap))
        row = self.cur.fetchone()
        if not do:
            return row
        if row:
            n.hash = row[0]
            n.id = row[1]
            n.timestamp = row[3]
            n.serial = row[4]
            n.deser(row[2])
            n.compress = row[5]
            return n
            if _debug:
                print "DB: %s, Selected row: %s" % (self.path, row)
        else:
            return None

    def _insert_row(self, n, ser):
        self.cur.execute("""INSERT INTO needles VALUES (?, ?, ?, ?, ?, ?)""",
                         (n.hash, n.id, ser, n.timestamp, n.serial, n.compress))
        if _debug:
            print "DB: %s, Inserted new row: %s" % (self.path, n)

    def _update_row(self, n, ser):
        self.cur.execute("""UPDATE needles SET data = ?, timestamp = ?, ser = ?,
                         compress = ?  WHERE hash = ?;""",
                         (ser, n.timestamp, n.serial, n.compress, n.hash))
        if _debug:
            print "DB: %s, Updated Exsiting row: %s" % (self.path, n)

    def _delete_row(self, n):
        self.cur.execute("""DELETE FROM needles WHERE hash = ?;""", (n.hash,))
        if _debug:
            print "DB: %s, Deleted Exsiting row: %s" % (self.path, n)

    def _drop_table(self):
        self.cur.execute("""DROP TABLE IF EXISTS needles;""")
        if _debug:
            print "DB: %s, Deleted Table" % self.path

    def close(self):
        if not self.isclosed:
            self._close_db()
        self.__closed = True

    def iterate(self):
        self.cur.execute("""SELECT * FROM needles""")
        return self.cur.fetchall()

    def throw(self, id, data):
        if _debug:
            print "DB: %s, Throwing to haystack with %s" % (self.path, id)
        ts = time.time()
        n = needle(id, data, ts, self.serial, self.compress)
        ser = n.ser()
        if self._select_row(n, -1, False):
            self._update_row(n, ser)
        else:
            self._insert_row(n, ser)
        return n

    def lose(self, id, hsh=None):
        if _debug:
            print "DB: %s, Deleting haystack with %s" % (self.path, id)
        n = needle(id, None, None)
        if hsh:
            n.hash = hsh
        else:
            n.dohash()
        self._delete_row(n)
        return n

    def find(self, id=None, hsh=None, since=0):
        if _debug:
            print "DB: %s, Fetching haystack with %s" % (self.path, id)
        n = needle(id, None, None, self.serial, self.compress)
        if hsh:
            n.hash = hsh
        else:
            n.dohash()
        if not self._select_row(n, since):
            n.data = {}
            n.timestamp = time.time()
        return n

    def snapshot(self):
        if isinstance(self.maxrows, int):
            self.cur.execute("""DELETE FROM needles WHERE hash NOT IN (SELECT hash FROM
                            needles ORDER BY timestamp DESC LIMIT ?)""", (self.maxrows,))
        self.conn.commit()
        if _debug:
            print "DB: %s, saved" % self.path

    def burn(self):
        self._drop_table()
        self._create_table()