import sys
import json
import urllib

cases = ("cases/mov_case_1.json",
         "cases/search_imdb.json",
         "cases/search_manual.json",
         )


def getclient(query):
    sys.argv = ["plugin://service.subtitles.turkcealtyazi", "1",
                "?" + query]
    import service
    from sublib import utils

    class testclass(service.turkcealtyazi):
        def oninit(self):
            for k, v in jscase["item"].iteritems():
                setattr(self.item, k, v)

    return testclass(utils.mozilla)


for case in cases:
    with open(case) as c:
        jscase = json.loads(c.read())
        client = getclient(urllib.urlencode(jscase["query"]))
        print "%s: running with query %s" % (case, jscase["query"])
        if jscase["query"]["action"] in ("search", "manualsearch"):
            print "%s: Search returned %s subtitles" % (case, len(client._subs))
        for i in xrange(jscase["download"]):
            jscase["query"]["action"] = "download"
            jscase["query"]["args"] = list(client._subs[i].args)
            jscase["query"]["kwargs"] = client._subs[i].kwargs
            from sublib.utils import dformat
            print "%s: Downloading subtitle %s" % (case, client._subs[i])
            q = dformat(jscase["query"], json.dumps)
            dclient = getclient(urllib.urlencode(q))
            pass
