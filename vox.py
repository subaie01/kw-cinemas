"""VOX Cinemas Kuwait — server-rendered HTML, parsed with BeautifulSoup."""
import re
import requests
from bs4 import BeautifulSoup

URL = "https://kwt.voxcinemas.com/movies/whatson"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

EXCLUDED_SLUGS = ("whatson", "comingsoon")


def fetch():
    """Return list of {title_en, language, booking_url, poster_src}."""
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    movies = []
    seen = set()
    for h3 in soup.select("h3 a[href*='/movies/']"):
        href = h3.get("href", "")
        slug = href.rstrip("/").split("/movies/")[-1]
        if not slug or slug in EXCLUDED_SLUGS or href in seen:
            continue
        seen.add(href)

        title = h3.get_text(strip=True)
        # language: slug suffix like -arabic / -turkish, else English
        m = re.search(r"-(arabic|turkish|hindi|tamil|malayalam|french)$", slug)
        language = m.group(1).capitalize() if m else "English"

        poster = None
        card = h3.find_parent()
        if card:
            img = card.find_previous("img")
            if img and "posters" in (img.get("src") or ""):
                poster = img["src"]

        movies.append({
            "title_en": title,
            "language": language,
            "booking_url": href if href.startswith("http") else f"https://kwt.voxcinemas.com{href}",
            "poster_src": poster,
        })
    return movies


if __name__ == "__main__":
    for m in fetch():
        print(m)
