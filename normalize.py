"""Merge the same movie across cinemas by normalizing titles into a key."""
import re
import unicodedata

NOISE = re.compile(
    r"\b(3d|2d|imax|4dx|atmos|mx4d|vip|gclass|the movie)\b|"
    r"\((arabic|english|turkish|egyptian|lebanese|kuwaiti|hindi)\)",
    re.I,
)
NON_ALNUM = re.compile(r"[^a-z0-9]+")

WORD_DIGITS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
}


def title_key(title):
    t = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    t = t.lower()
    t = NOISE.sub(" ", t)
    t = re.sub(r"\s*-\s*(english|arabic|turkish|hindi|french|malayalam|tamil|telugu)"
               r"([.\s]+(english|arabic))?\s*$", " ", t)
    words = [WORD_DIGITS.get(w, w) for w in NON_ALNUM.sub(" ", t).split()]
    if words and words[0] == "the":
        words = words[1:]
    return "".join(words)


def merge(listings_by_cinema):
    merged = {}
    for cinema_id, listings in listings_by_cinema.items():
        for item in listings:
            key = title_key(item["title_en"])
            if not key:
                continue
            entry = merged.setdefault(key, {
                "title_en": item["title_en"],
                "languages": set(),
                "cinemas": {},
                "poster_src": None,
            })
            if item.get("language"):
                entry["languages"].add(item["language"])
            entry["cinemas"].setdefault(cinema_id, item["booking_url"])
            if not entry["poster_src"] and item.get("poster_src"):
                entry["poster_src"] = item["poster_src"]
            for extra in ("title_ar", "synopsis_ar", "genres_ar",
                          "runtime_min", "trailer_youtube_id"):
                if item.get(extra) and not entry.get(extra):
                    entry[extra] = item[extra]
            if len(item["title_en"]) > len(entry["title_en"]):
                entry["title_en"] = item["title_en"]

    out = {}
    for key, e in merged.items():
        row = {
            "title_en": e["title_en"],
            "languages": sorted(e["languages"]),
            "cinemas": [{"id": c, "booking_url": u} for c, u in sorted(e["cinemas"].items())],
            "poster_src": e["poster_src"],
        }
        for extra in ("title_ar", "synopsis_ar", "genres_ar",
                      "runtime_min", "trailer_youtube_id"):
            if e.get(extra):
                row[extra] = e[extra]
        out[key] = row
    return out
