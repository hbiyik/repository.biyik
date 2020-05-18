meta_states = {0: "NEW",
               1: "TO BE REMOVED",
               2: "COMMITED",
               3: "UPDATED",
               1000: "LEGACY"
               }

dirty_metas = [0, 1, 6]

dl_states = {"DLSTATUS_ALLOCATING_DISKSPACE": "Allocating Disk Space",
             "DLSTATUS_WAITING4HASHCHECK": "Waiting to hashcheck",
             "DLSTATUS_HASHCHECKING": "Hashchecking",
             "DLSTATUS_DOWNLOADING": "Downloading",
             "DLSTATUS_SEEDING": "Seeding",
             "DLSTATUS_STOPPED": "Stopped",
             "DLSTATUS_STOPPED_ON_ERROR": "Error",
             "DLSTATUS_METADATA": "Waiting for metadata",
             "DLSTATUS_CIRCUITS": "Establishing Circuits",
             "DLSTATUS_EXIT_NODES": "Waiting for exit nodes"
             }

dl_states_short = {"DOWNLOADING": ["DLSTATUS_DOWNLOADING"],
                   "WAITING": ["DLSTATUS_ALLOCATING_DISKSPACE", "DLSTATUS_WAITING4HASHCHECK",
                               "DLSTATUS_HASHCHECKING", "DLSTATUS_METADATA",
                               "DLSTATUS_CIRCUITS", "DLSTATUS_EXIT_NODES"],
                   "SEEDING": ["DLSTATUS_SEEDING"],
                   "STOPPED": ["DLSTATUS_STOPPED", "DLSTATUS_STOPPED_ON_ERROR"]
                   }

YES = "[COLOR yellowgreen]Y[/COLOR]"
NO = "[COLOR red]N[/COLOR]"


def BLUE(txt):
    return "[COLOR blue]%s[/COLOR]" % txt


DHT_TIMEOUT = 30
HTTP_TIMEOUT = 60

MIN_TRIBLER_VERSION = "7.5"
TORRENT_UPDATE_INTERVAL = 1
