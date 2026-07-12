"""Sky Cinemas Kuwait — homepage is server-rendered; NOW SHOWING cards carry
links of the form /movie-information/<slug>/<id>/NowShowing."""
import re
import requests
from bs4 import BeautifulSoup

URL = "https://www.skycinemaskw.com/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def clean_title(raw):
    """'MOANA - ENGLISH' -> ('Moana', 'English');
    'SAKR W CANARIA (EGYPTIAN) - ARABIC' -> ('Sakr W Canaria', 'Arabic')"""
    t = raw.strip()
    language = "English"
    m = re.search(r"-\s*(ENGLISH|ARABIC|HINDI|TURKISH)\s*$", t, re.I)
    if m:
        language = m.group(1).capitalize()
        t = t[: m.start()].strip()
    t = re.sub(r"\((EGYPTIAN|LEBANESE|KUWAITI|INDIAN)\)", "", t, flags=re.I).strip()
    return t.title(), language


def fetch():
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    movies, seen = [], set()
    # Any movie-information link ending in /NowShowing (skip the VIP duplicates
    # and the date-time-quantity booking-flow links).
    for a in soup.select("a[href*='/movie-information/']"):
        href = a.get("href", "")
        if "/NowShowing" not in href or "date-time-quantity" in href:
            continue
        parts = [p for p in href.split("/") if p]
        movie_id = next((p for p in parts if p.isdigit()), None)
        if not movie_id or movie_id in seen:
            continue
        seen.add(movie_id)

        # Title lives in the nearest preceding h3, or the card img alt.
        h3 = a.find_previous("h3")
        img = a.find_previous("img")
        raw = (h3.get_text(strip=True) if h3 else "") or ((img.get("title") or img.get("alt")) if img else "")
        # h3 text can be visually truncated ('EBEN MEEN FEHOM (EGYPTIAN) -...');
        # prefer the img title when the h3 ends with an ellipsis.
        if raw.endswith("...") and img is not None:
            raw = img.get("title") or img.get("alt") or raw
        if not raw:
            continue

        title, language = clean_title(raw)
        movies.append({
            "title_en": title,
            "language": language,
            "booking_url": href if href.startswith("http") else f"https://www.skycinemaskw.com{href}",
            "poster_src": f"https://www.skycinemaskw.com/images/movies/{movie_id}.jpg",
        })
    return movies


if __name__ == "__main__":
    for m in fetch():
        print(m)
