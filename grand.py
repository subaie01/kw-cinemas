"""Grand Cinemas Kuwait — server-rendered HTML at kw.grandcinemasme.com.

Strategy (deliberately structure-independent, so site redesigns rarely break it):
- Now-showing movies are the ones with a booking link ('Book Now' / 'احجز الآن')
  pointing at /movie/<slug>/..; coming-soon cards only carry trailer links.
- The English title is derived from the slug ('toy-story-5' -> 'Toy Story 5'),
  which is exactly what we need for TMDB matching. Display titles come from
  TMDB later anyway.
"""
import re
import requests
from bs4 import BeautifulSoup

URL = "https://kw.grandcinemasme.com/en"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

BOOK_TEXT = ("book now", "احجز الآن")
# Screenings that aren't movies (sports broadcasts etc.)
BLOCKLIST = re.compile(r"world-cup|fifa|wwe|ufc|concert", re.I)
MOVIE_HREF = re.compile(r"/movie/([^/]+)(?:/(en|ar))?/?$")


def slug_to_title(slug):
    words = slug.replace("--", "-").split("-")
    return " ".join(w.capitalize() for w in words if w)


def fetch():
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    movies, seen = [], set()
    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True).lower()
        if text not in BOOK_TEXT:
            continue
        m = MOVIE_HREF.search(a["href"])
        if not m:
            continue
        slug = m.group(1)
        if slug in seen or BLOCKLIST.search(slug):
            continue
        seen.add(slug)
        movies.append({
            "title_en": slug_to_title(slug),
            "language": None,
            "booking_url": f"https://kw.grandcinemasme.com/movie/{slug}/en",
            "poster_src": None,  # posters are lazy-loaded; TMDB supplies them
            "slug": slug,
        })
    return movies


if __name__ == "__main__":
    for m in fetch():
        print(m)
