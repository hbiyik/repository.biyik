'''
Created on Jun 25, 2025

@author: boogie
'''
from tinyxbmc import net
import json
import random


TMDB_URL = "https://api.themoviedb.org/3"
TMDB_KEY = "f090bb54758cabf231fb605d3e3e0468"

DETAILS_MAIN = "main"
DETAILS_SEASON = "season"
DETAILS_EPISODE = "episode"
DETAILS_CONFIG = "configuration"

API_ENDPOINT_VIDEOS = "videos"
API_ENDPOINT_KEYWORDS = "keywords"
API_ENDPOINT_IMAGES = "images"
API_ENDPOINT_CREDITS = "credits"
API_ENDPOINT_FIND = "find"
API_PARAM_KEY = "api_key"
API_PARAM_APPEND = "append_to_response"
API_PARAM_SOURCE = "external_source"
API_PARAM_LANGUAGE = "language"
API_PARAM_IMAGE_LANGUAGE = "include_image_language"

DEFAULT_LANGUAGE = "en"

DETAILS_LOOKUP = DETAILS_EPISODE, DETAILS_SEASON, DETAILS_MAIN
DETAILS_LOOKUP_REVERSE = DETAILS_MAIN, DETAILS_SEASON, DETAILS_EPISODE

CACHETIME = None


def findimdb(imdbid, tv=False):
    u = f"{TMDB_URL}/{API_ENDPOINT_FIND}/{imdbid}"
    p = {API_PARAM_KEY: TMDB_KEY,
         API_PARAM_SOURCE: "imdb_id"}
    result = json.loads(net.http(u, params=p, cache=CACHETIME))
    if not tv:
        return result.get("movie_results", [])
    else:
        return result.get("tv_results", [])


def fetchdetails(details, key, u, params, lang):
    params[API_PARAM_LANGUAGE] = lang
    details[key] = [json.loads(net.http(u, params=params, cache=CACHETIME))]
    # some texts are not available in local langauges for some medias,
    # fallback to default lanuague in such a case
    if not lang == DEFAULT_LANGUAGE:
        p_en = {API_PARAM_KEY: TMDB_KEY, API_PARAM_LANGUAGE: DEFAULT_LANGUAGE}
        details[key].append(json.loads(net.http(u, params=p_en, cache=CACHETIME)))


def getdetails(tmdbid, media_type="movie", season=None, episode=None, lang=DEFAULT_LANGUAGE):
    details = {}
    image_langs = "en,null"
    if not lang == DEFAULT_LANGUAGE:
        image_langs += f",{DEFAULT_LANGUAGE[:2]}"

    u = f"{TMDB_URL}/{media_type}/{tmdbid}"
    p = {API_PARAM_KEY: TMDB_KEY,
         API_PARAM_APPEND: f"{API_ENDPOINT_VIDEOS},{API_ENDPOINT_IMAGES},{API_ENDPOINT_CREDITS},{API_ENDPOINT_KEYWORDS}",
         API_PARAM_IMAGE_LANGUAGE: image_langs}
    fetchdetails(details, DETAILS_MAIN, u, p, lang)

    if season is not None:
        u = f"{TMDB_URL}/{media_type}/{tmdbid}/{DETAILS_SEASON}/{season}"
        p = {API_PARAM_KEY: TMDB_KEY,
             API_PARAM_APPEND: f"{API_ENDPOINT_VIDEOS},{API_ENDPOINT_IMAGES},{API_ENDPOINT_CREDITS}",
             API_PARAM_IMAGE_LANGUAGE: image_langs}
        fetchdetails(details, DETAILS_SEASON, u, p, lang)
    else:
        details[DETAILS_SEASON] = []

    if season is not None and episode is not None:
        u = f"{TMDB_URL}/{media_type}/{tmdbid}/{DETAILS_SEASON}/{season}/{DETAILS_EPISODE}/{episode}"
        p = {API_PARAM_KEY: TMDB_KEY,
             API_PARAM_APPEND: f"{API_ENDPOINT_VIDEOS},{API_ENDPOINT_IMAGES},{API_ENDPOINT_CREDITS}",
             API_PARAM_IMAGE_LANGUAGE: image_langs}
        fetchdetails(details, DETAILS_EPISODE, u, p, lang)
    else:
        details[DETAILS_EPISODE] = {}

    u = f"{TMDB_URL}/{DETAILS_CONFIG}"
    p = {API_PARAM_KEY: TMDB_KEY}
    details[DETAILS_CONFIG] = json.loads(net.http(u, params=p, cache=CACHETIME))
    return details


def getimgbaseurl(config, imgsizes, key=-1):
    return f"{config['images']['secure_base_url']}{config['images'][imgsizes][key]}"


def kodiart(details, lang=DEFAULT_LANGUAGE):
    art = {}
    keymaps = [("fanart", "backdrop_path", "backdrops", "backdrop_sizes"),
               ("poster", "still_path", "stills", "still_sizes"),
               ("poster", "poster_path", "posters", "poster_sizes"),
               ("thumb", "logo_path", "logos", "logo_sizes"),
               ("icon", "logo_path", "logos", "logo_sizes")]

    for lookup in DETAILS_LOOKUP:
        for detail in details[lookup]:
            images = detail.get("images", {})
            if not images:
                continue
            for artkey, _, imgkey, imgsizes in keymaps:
                if artkey in art:
                    continue
                img_none = []
                img_en = []
                img_local = []
                for img in images.get(imgkey, []):
                    for lst, check in [(img_none, None),
                                       (img_en, DEFAULT_LANGUAGE),
                                       (img_local, lang)]:
                        if img.get("iso_639_1") == check:
                            lst.append(img.get("file_path"))
                img = img_local or img_en or img_none
                if not img:
                    continue
                art[artkey] = getimgbaseurl(details[DETAILS_CONFIG], imgsizes) + random.choice(img)

            for artkey, reskey, _, imgsizes in keymaps:
                if reskey not in detail:
                    continue
                if artkey in art:
                    continue
                art[artkey] = detail[reskey]

    return art


def get_crew(details, department, jobs):
    result = []
    for look in DETAILS_LOOKUP:
        for detail in details[look]:
            if not detail:
                continue
            for crew in detail.get("credits", {}).get("crew", []):
                if crew['department'] == department and crew['job'] in jobs and crew['name'] not in result:
                    result.append(crew['name'])
            if result:
                return result
    return result


def searchvalue(details, *keys, lookup=DETAILS_LOOKUP):
    subval = None
    for look in lookup:
        for val in details[look]:
            for key in keys:
                subval = val.get(key)
                if not subval:
                    break
                val = subval
            if subval:
                return subval


def kodiinfo(details, istv=False, season=None, episode=None):
    if istv:
        info = {'tvshowtitle': searchvalue(details, 'name', lookup=DETAILS_LOOKUP_REVERSE),
                'originaltitle': searchvalue(details, 'original_name', lookup=DETAILS_LOOKUP_REVERSE),
                }
        if episode:
            info = {'title': searchvalue(details, 'name', lookup=[DETAILS_EPISODE])}
        elif season:
            info = {'title': searchvalue(details, 'name', lookup=[DETAILS_SEASON])}
    else:
        info = {'title': searchvalue(details, 'title'),
                'originaltitle': searchvalue(details, 'original_title'),
                }

    for infokey, reskey in (("plot", "overview"),
                            ("tagline", "tagline"),
                            ("premiered", "release_date"),
                            ("premiered", "first_air_date")):
        val = searchvalue(details, reskey)
        if not val:
            continue
        info[infokey] = val

    release_date = searchvalue(details, "release_date", lookup=DETAILS_LOOKUP_REVERSE)
    if release_date:
        info["year"] = int(release_date[:4])

    for infokey, resnamekey in (("studio", "production_companies"),
                                ("genre", "genres"),
                                ("country", "production_countries")):
        info[infokey] = [x["name"] for x in searchvalue(details, resnamekey) or []]

    info["cast"] = [(x["name"], x["character"]) for x in searchvalue(details, "credits", "cast") or []]

    info['credits'] = get_crew(details, 'Writing', ['Screenplay', 'Writer', 'Author'])
    info['director'] = get_crew(details, 'Directing', ['Director', 'Series Director'])

    runtime = searchvalue(details, "runtime")
    if runtime:
        info['duration'] = runtime * 60

    return info


def query(imdbid, istv=False, season=None, episode=None, lang="en-US"):
    results = findimdb(imdbid, istv)
    if not results:
        return
    return getdetails(results[0]["id"], results[0]["media_type"], season, episode, lang)
