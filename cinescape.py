"""Cinescape Kuwait — JSON API used by their React site."""
import re
import requests

API_URL = "https://api.cinescape.com.kw/api/content/nowshowing"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Content-Type": "application/json",
    "Origin": "https://www.cinescape.com.kw",
    "Referer": "https://www.cinescape.com.kw/movies",
}


def youtube_id(url):
    if not url:
        return None
    m = re.search(r"(?:youtu\.be/|v=|/embed/)([A-Za-z0-9_-]{6,})", url)
    return m.group(1) if m else None


def slugify(title):
    return title.strip().lower().replace(" ", "-")


def fetch():
    resp = requests.post(API_URL, json={}, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    output = resp.json().get("output", [])

    movies = []
    for m in output:
        if m.get("comingSoon"):
            continue
        title = (m.get("title") or "").strip()
        if not title:
            continue
        booking = (m.get("shareUrl") or "").strip() or \
            f"https://www.cinescape.com.kw/moviesessions/{slugify(title)}/{m['id']}"
        genres_ar = [g.strip() for g in
                     re.split(r"[,،]", m.get("genreAlt") or "") if g.strip()]
        movies.append({
            "title_en": title,
            "language": (m.get("language") or "").strip() or None,
            "booking_url": booking,
            "poster_src": m.get("webimgsmall") or m.get("mobimgsmall"),
            "title_ar": (m.get("titleAlt") or "").strip() or None,
            "synopsis_ar": (m.get("synopsisAlt") or "").strip() or None,
            "genres_ar": genres_ar or None,
            "runtime_min": m.get("runTime") or None,
            "trailer_youtube_id": youtube_id(m.get("trailerUrl")),
        })
    return movies
