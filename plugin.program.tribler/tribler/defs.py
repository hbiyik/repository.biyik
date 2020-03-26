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
