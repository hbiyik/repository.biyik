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
from threading import Lock
try:
    import cPickle as pickle
except ImportError:
    import pickle as pickle
from tinyxbmc import addon

import sqlite3
import six
_debug = False


def _null(data, *args, **kwargs):
    return data


class needle():
    def __init__(self, nid=None, data=None, timestamp=None, serial=None, compress=0):
        self.compress = compress
        self.id = nid
        self.data = data
        self.timestamp = timestamp
        if serial is None:
            self.serial = "p_%s" % pickle.HIGHEST_PROTOCOL
        else:
            self.serial = serial
        self.hash = None

    def __repr__(self):
        return repr({"hash": self.hash,
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
        try:
            serdata = zlib.decompress(serdata)
        except Exception:
            if six.PY2:
                serdata = str(serdata)

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
            serdata = pickle.dumps(self.data, protocol)
        elif self.serial == "json":
            serdata = json.dumps(self.data)
            if six.PY3:
                serdata = serdata.encode()
        elif self.serial == "null":
            serdata = self.data

        serdata = sqlite3.Binary(comp(serdata))
        self.dohash(serdata)
        return serdata


class stack(object):
    def __init__(self, path, serial=None, compress=0, maxrows=5000, write=True, aid=None):
        self.write = write
        self.mutex = Lock()
        self.compress = compress
        self.maxrows = maxrows
        self.path = path
        self.addon = aid
        if aid is not None:
            bpath = addon.get_addondir(self.addon)
        else:
            bpath = addon.get_commondir()
        path = os.path.join(bpath, path)
        if not os.path.exists(path):
            os.makedirs(path)
        self.dbpath = os.path.join(path, "haystack.db")
        self._open_db(self.dbpath)
        if not self._check_db():
            self._create_table()
        self.serial = serial
        self.__closed = False

    @property
    def isclosed(self):
        return self.__closed

    def __execute(self, *args, **kwargs):
        with Mutex(self.mutex):
            try:
                self.cur.execute(*args, **kwargs)
            except Exception:
                if os.path.exists(self.dbpath):
                    os.remove(self.dbpath)
                self.__init__(self.path, self.serial, self.compress, self.maxrows, self.write, self.addon)
                addon.log("DB: DB is locked, renewed the cache: %s" % self.dbpath)
                self.cur.execute(*args, **kwargs)

    def __enter__(self):
        self.ts = time.time()
        return self

    def __exit__(self, typ, value, traceback):
        self.close()
        if _debug:
            optime = (time.time() - self.ts) * 1000
            addon.log("DB: %s, Operation Time (ms): %s " % (self.path, optime))

    def __del__(self):
        try:
            self.close()
        except:
            pass

    def _check_db(self):
        columns = [u"hash", u"id", u"data", u"timestamp", u"ser", u"compress"]
        self.__execute("""PRAGMA table_info(needles)""")
        k = 0
        with Mutex(self.mutex):
            for row in self.cur:
                if not row[1] == columns[k]:
                    break
                k += 1
        return k == 6

    def _create_table(self):
        if _debug:
            addon.log("DB: %s, Created a new haystack" % self.path)
        with Mutex(self.mutex):
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
            addon.log("DB: %s, opened at %s" % (self.path, path))
        with Mutex(self.mutex):
            self.conn = sqlite3.connect(path, check_same_thread=False)
            self.cur = self.conn.cursor()
            self.cur.executescript("""
                                   PRAGMA JOURNAL_MODE = MEMORY;
                                   PRAGMA SYNCHRONOUS = OFF;
                                   PRAGMA LOCKING_MODE = UNLOCKED;""")

    def _close_db(self):
        if self.write:
            self.snapshot()
        with Mutex(self.mutex):
            self.cur.close()
            self.conn.close()
        if _debug:
            addon.log("DB: %s, saved and closed" % self.path)

    def _select_row(self, n, since=0, do=True):
        if since > 0:
            gap = time.time() - since * 60 * 60
        else:
            gap = 0
        self.__execute("""SELECT * FROM needles WHERE hash=? and timestamp >= ? LIMIT 1;""",
                       (n.hash, gap))
        with Mutex(self.mutex):
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
                addon.log("DB: %s, Selected row: %s" % (self.path, row))
        else:
            return None

    def _insert_row(self, n, ser):
        self.__execute("""INSERT INTO needles VALUES (?, ?, ?, ?, ?, ?)""",
                       (n.hash, n.id, ser, n.timestamp, n.serial, n.compress))
        if _debug:
            addon.log("DB: %s, Inserted new row: %s" % (self.path, n))

    def _update_row(self, n, ser):
        self.__execute("""UPDATE needles SET data = ?, timestamp = ?, ser = ?, compress = ?  WHERE hash = ?;""",
                       (ser, n.timestamp, n.serial, n.compress, n.hash))
        if _debug:
            addon.log("DB: %s, Updated Exsiting row: %s" % (self.path, n))

    def _delete_row(self, n):
        self.__execute("""DELETE FROM needles WHERE hash = ?;""", (n.hash,))
        if _debug:
            addon.log("DB: %s, Deleted Exsiting row: %s" % (self.path, n))

    def _drop_table(self):
        self.__execute("""DROP TABLE IF EXISTS needles;""")
        if _debug:
            addon.log("DB: %s, Deleted Table" % self.path)

    def close(self):
        if not self.isclosed:
            self._close_db()
        self.__closed = True

    def iterate(self):
        self.__execute("""SELECT * FROM needles""")
        with Mutex(self.mutex):
            return self.cur.fetchall()

    def throw(self, nid, data):
        if _debug:
            addon.log("DB: %s, Throwing to haystack with %s" % (self.path, nid))
        ts = time.time()
        n = needle(nid, data, ts, self.serial, self.compress)
        ser = n.ser()
        if self._select_row(n, -1, False):
            self._update_row(n, ser)
        else:
            self._insert_row(n, ser)
        return n

    def lose(self, nid, hsh=None):
        if _debug:
            addon.log("DB: %s, Deleting haystack with %s" % (self.path, nid))
        n = needle(nid, None, None)
        if hsh:
            n.hash = hsh
        else:
            n.dohash()
        self._delete_row(n)
        return n

    def find(self, nid=None, hsh=None, since=0):
        if _debug:
            addon.log("DB: %s, Fetching haystack with %s" % (self.path, nid))
        n = needle(nid, None, None, self.serial, self.compress)
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
            self.__execute("""DELETE FROM needles WHERE hash NOT IN (SELECT hash FROM
                            needles ORDER BY timestamp DESC LIMIT ?)""", (self.maxrows,))
        with Mutex(self.mutex):
            try:
                self.conn.commit()
            except sqlite3.OperationalError:
                return
        if _debug:
            addon.log("DB: %s, saved" % self.path)

    def burn(self):
        self._drop_table()
        self._create_table()


class Mutex(object):
    def __init__(self, mutex):
        self.mutex = mutex

    def __enter__(self, *args, **kwargs):
        self.mutex.acquire()
        return self.mutex

    def __exit__(self, *args, **kwargs):
        self.mutex.release()
