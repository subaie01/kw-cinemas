"""Stage 2: enrich raw listings — NO accounts / API keys needed."""
import gzip
import io
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw_listings.json"
OUT = ROOT / "data" / "movies.json"
CACHE_DIR = ROOT / "data" / "cache"
OVERRIDES = ROOT / "overrides.json"

WD_API = "https://www.wikidata.org/w/api.php"
IMDB_RATINGS_URL = "https://datasets.imdbws.com/title.ratings.tsv.gz"
HEADERS = {"User-Agent": "KWCinemasAggregator/1.0 (movie listing aggregator; contact: alsubaiei.a@gmail.com)"}

FILM_TYPES = {"Q11424", "Q202866", "Q24862", "Q226730", "Q20667187", "Q229390"}
RT_QID = "Q105584"

CINEMAS = {
    "cinescape": {"name_ar": "سينسكيب"},
    "vox": {"name_ar": "ڤوكس سينما"},
    "grand": {"name_ar": "جراند سينما"},
    "sky": {"name_ar": "سكاي سينما"},
}


def wd_get(**params):
    params.update(format="json")
    r = requests.get(WD_API, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def wd_search(title):
    res = wd_get(action="wbsearchentities", search=title, language="en",
                 type="item", limit=7)
    return [x["id"] for x in res.get("search", [])]


def wd_entities(qids, props="claims|labels|sitelinks", languages=None):
    if not qids:
        return {}
    out = {}
    for i in range(0, len(qids), 50):
        params = dict(action="wbgetentities", ids="|".join(qids[i:i + 50]),
                      props=props)
        if languages:
            params["languages"] = languages
        out.update(wd_get(**params).get("entities", {}))
        time.sleep(0.3)
    return out


def claim_values(claims, prop):
    vals = []
    for st in claims.get(prop, []):
        dv = (st.get("mainsnak") or {}).get("datavalue")
        if dv is not None:
            vals.append((dv.get("value"), st.get("qualifiers", {})))
    return vals


def first_str(claims, prop):
    for v, _ in claim_values(claims, prop):
        if isinstance(v, str):
            return v
    return None


def release_date(claims):
    dates = [v.get("time", "") for v, _ in claim_values(claims, "P577")
             if isinstance(v, dict)]
    if not dates:
        return None
    return min(dates).lstrip("+")[:10]


def is_film(claims):
    for v, _ in claim_values(claims, "P31"):
        if isinstance(v, dict) and (v.get("id") in FILM_TYPES):
            return True
    return False


def rt_score(claims):
    best, best_time = None, ""
    for v, quals in claim_values(claims, "P444"):
        if not isinstance(v, str) or "%" not in v:
            continue
        by = [q.get("datavalue", {}).get("value", {}).get("id")
              for q in quals.get("P447", [])]
        if by and RT_QID not in by:
            continue
        t = ""
        for q in quals.get("P585", []):
            t = max(t, q.get("datavalue", {}).get("value", {}).get("time", ""))
        if best is None or t >= best_time:
            best, best_time = v, t
    return best


def runtime_minutes(claims):
    for v, _ in claim_values(claims, "P2047"):
        if isinstance(v, dict):
            try:
                return int(float(v.get("amount", "0").lstrip("+")))
            except ValueError:
                pass
    return None


def pick_film_entity(qids):
    entities = wd_entities(qids)
    films = [(e, release_date(e.get("claims", {})) or "0000")
             for e in entities.values() if is_film(e.get("claims", {}))]
    if not films:
        return None
    films.sort(key=lambda x: x[1], reverse=True)
    return films[0][0]


def arwiki_summary(title):
    url = f"https://ar.wikipedia.org/api/rest_v1/page/summary/{quote(title.replace(' ', '_'))}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    if r.status_code != 200:
        return ""
    return (r.json().get("extract") or "").strip()


def genre_labels_ar(genre_qids):
    ents = wd_entities(genre_qids, props="labels", languages="ar|en")
    out = {}
    for qid, e in ents.items():
        labels = e.get("labels", {})
        out[qid] = (labels.get("ar") or labels.get("en") or {}).get("value")
    return out


def load_imdb_ratings(imdb_ids):
    wanted = set(filter(None, imdb_ids))
    if not wanted:
        return {}
    r = requests.get(IMDB_RATINGS_URL, headers=HEADERS, timeout=120)
    r.raise_for_status()
    ratings = {}
    with gzip.open(io.BytesIO(r.content), "rt", encoding="utf-8") as f:
        next(f)
        for line in f:
            tconst, rating, _ = line.rstrip("\n").split("\t")
            if tconst in wanted:
                ratings[tconst] = rating
                if len(ratings) == len(wanted):
                    break
    return ratings


def enrich_one(key, raw, overrides):
    ov = overrides.get(key, {})
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists() and not ov.get("refresh"):
        return json.loads(cache_file.read_text(encoding="utf-8"))

    entity = None
    if ov.get("wikidata_qid"):
        entity = wd_entities([ov["wikidata_qid"]]).get(ov["wikidata_qid"])
    else:
        qids = wd_search(raw["title_en"])
        time.sleep(0.3)
        if qids:
            entity = pick_film_entity(qids)

    title_en = raw["title_en"]
    movie = {
        "id": f"local-{key}",
        "title_ar": ov.get("title_ar") or raw.get("title_ar") or title_en,
        "title_en": title_en,
        "synopsis_ar": ov.get("synopsis_ar") or raw.get("synopsis_ar") or "",
        "genres_ar": ov.get("genres_ar") or raw.get("genres_ar") or [],
        "runtime_min": raw.get("runtime_min"),
        "poster": raw.get("poster_src"),
        "trailer_youtube_id": ov.get("trailer_youtube_id")
                              or raw.get("trailer_youtube_id"),
        "trailer_search_url":
            f"https://www.youtube.com/results?search_query={quote(title_en + ' official trailer')}",
        "ratings": {},
        "imdb_id": None,
        "release_date": None,
        "matched": False,
    }

    if entity:
        claims = entity.get("claims", {})
        labels = entity.get("labels", {})
        sitelinks = entity.get("sitelinks", {})

        movie["id"] = f"wd-{entity.get('id', key)}"
        movie["matched"] = True
        movie["imdb_id"] = first_str(claims, "P345")
        movie["release_date"] = release_date(claims)
        movie["runtime_min"] = runtime_minutes(claims) or movie["runtime_min"]

        ar_label = (labels.get("ar") or {}).get("value")
        if not ov.get("title_ar") and ar_label:
            movie["title_ar"] = ar_label

        rt = rt_score(claims)
        if rt:
            movie["ratings"]["rotten_tomatoes"] = rt

        if not movie["genres_ar"]:
            genre_qids = [v["id"] for v, _ in claim_values(claims, "P136")
                          if isinstance(v, dict)]
            if genre_qids:
                names = genre_labels_ar(genre_qids)
                movie["genres_ar"] = [n for n in
                                      (names.get(q) for q in genre_qids) if n]

        if not movie["synopsis_ar"]:
            arwiki = (sitelinks.get("arwiki") or {}).get("title")
            if arwiki:
                movie["synopsis_ar"] = arwiki_summary(arwiki)
                time.sleep(0.3)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(movie, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    return movie


def main():
    raw_data = json.loads(RAW.read_text(encoding="utf-8"))
    overrides = (json.loads(OVERRIDES.read_text(encoding="utf-8"))
                 if OVERRIDES.exists() else {})
    overrides.pop("_comment", None)

    movies, unmatched = [], []
    for key, raw in raw_data["movies"].items():
        m = enrich_one(key, raw, overrides)
        m["languages"] = raw.get("languages", [])
        m["cinemas"] = raw["cinemas"]
        movies.append(m)
        if not m["matched"]:
            unmatched.append(raw["title_en"])

    imdb_map = load_imdb_ratings([m["imdb_id"] for m in movies])
    for m in movies:
        if m["imdb_id"] in imdb_map:
            m["ratings"]["imdb"] = imdb_map[m["imdb_id"]]

    movies.sort(key=lambda m: m.get("release_date") or "", reverse=True)

    OUT.write_text(json.dumps({
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "cinemas": CINEMAS,
        "movies": movies,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{len(movies)} movies -> {OUT}")
    if unmatched:
        print("UNMATCHED on Wikidata (fixable via overrides.json):", unmatched)


if __name__ == "__main__":
    main()
