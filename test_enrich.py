import gzip, json, sys, os, shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).parent))
import enrich

QID = "Q999001"
SEARCH = {"search": [{"id": "Q111"}, {"id": QID}]}
OLD_FILM = {  # 1981 namesake — must NOT be picked
    "id": "Q111",
    "claims": {
        "P31": [{"mainsnak": {"datavalue": {"value": {"id": "Q11424"}}}}],
        "P577": [{"mainsnak": {"datavalue": {"value": {"time": "+1981-04-10T00:00:00Z"}}}}],
    }, "labels": {}, "sitelinks": {},
}
NEW_FILM = {
    "id": QID,
    "claims": {
        "P31": [{"mainsnak": {"datavalue": {"value": {"id": "Q11424"}}}}],
        "P577": [{"mainsnak": {"datavalue": {"value": {"time": "+2026-06-25T00:00:00Z"}}}}],
        "P345": [{"mainsnak": {"datavalue": {"value": "tt9999999"}}}],
        "P2047": [{"mainsnak": {"datavalue": {"value": {"amount": "+110", "unit": "u"}}}}],
        "P136": [{"mainsnak": {"datavalue": {"value": {"id": "Q200092"}}}}],
        "P444": [
            {"mainsnak": {"datavalue": {"value": "70%"}},
             "qualifiers": {"P447": [{"datavalue": {"value": {"id": "Q105584"}}}],
                            "P585": [{"datavalue": {"value": {"time": "+2026-06-30T00:00:00Z"}}}]}},
            {"mainsnak": {"datavalue": {"value": "85%"}},
             "qualifiers": {"P447": [{"datavalue": {"value": {"id": "Q105584"}}}],
                            "P585": [{"datavalue": {"value": {"time": "+2026-07-10T00:00:00Z"}}}]}},
            {"mainsnak": {"datavalue": {"value": "7.1/10"}},
             "qualifiers": {"P447": [{"datavalue": {"value": {"id": "Q37312"}}}]}},
        ],
    },
    "labels": {"ar": {"value": "إيفل ديد بيرن"}},
    "sitelinks": {"arwiki": {"title": "إيفل ديد بيرن"}},
}
GENRES = {"entities": {"Q200092": {"labels": {"ar": {"value": "رعب"}}}}}
SUMMARY = {"extract": "فيلم رعب أمريكي صدر عام 2026."}

tsv = "tconst\taverageRating\tnumVotes\ntt0000001\t5.5\t100\ntt9999999\t7.3\t5000\n"
GZ = gzip.compress(tsv.encode())

def fake_get(url, params=None, headers=None, timeout=None):
    r = MagicMock(); r.raise_for_status = lambda: None; r.status_code = 200
    p = params or {}
    if "wikidata" in url and p.get("action") == "wbsearchentities":
        r.json = lambda: SEARCH
    elif "wikidata" in url and p.get("action") == "wbgetentities":
        ids = p["ids"].split("|")
        if "Q200092" in ids: r.json = lambda: GENRES
        else: r.json = lambda: {"entities": {e["id"]: e for e in (OLD_FILM, NEW_FILM) if e["id"] in ids}}
    elif "ar.wikipedia" in url:
        r.json = lambda: SUMMARY
    elif "imdbws" in url:
        r.content = GZ
    else:
        raise AssertionError(url)
    return r

enrich.CACHE_DIR = Path("/tmp/kwe_cache"); shutil.rmtree("/tmp/kwe_cache", ignore_errors=True)

with patch.object(enrich.requests, "get", fake_get), patch.object(enrich.time, "sleep"):
    m = enrich.enrich_one("evildeadburn", {"title_en": "Evil Dead Burn", "poster_src": "https://x/p.jpg"}, {})
    assert m["id"] == f"wd-{QID}", m["id"]
    assert m["title_ar"] == "إيفل ديد بيرن"
    assert m["ratings"] == {"rotten_tomatoes": "85%"}, m["ratings"]
    assert m["genres_ar"] == ["رعب"]
    assert m["runtime_min"] == 110
    assert m["synopsis_ar"].startswith("فيلم رعب")
    assert m["imdb_id"] == "tt9999999"
    assert m["poster"] == "https://x/p.jpg"
    assert m["release_date"] == "2026-06-25"
    ratings = enrich.load_imdb_ratings([m["imdb_id"]])
    assert ratings == {"tt9999999": "7.3"}, ratings

# cache: no network on 2nd call
with patch.object(enrich.requests, "get", side_effect=AssertionError("network hit")):
    m2 = enrich.enrich_one("evildeadburn", {"title_en": "Evil Dead Burn"}, {})
    assert m2["title_ar"] == "إيفل ديد بيرن"

# unmatched movie falls back gracefully
def none_get(url, params=None, headers=None, timeout=None):
    r = MagicMock(); r.raise_for_status = lambda: None
    r.json = lambda: {"search": []}
    return r
with patch.object(enrich.requests, "get", none_get), patch.object(enrich.time, "sleep"):
    u = enrich.enrich_one("sakrwcanaria", {"title_en": "Sakr W Canaria", "poster_src": None}, {})
    assert not u["matched"] and u["title_ar"] == "Sakr W Canaria"
    assert "youtube.com/results" in u["trailer_search_url"]

print("enrich v2 ok")
