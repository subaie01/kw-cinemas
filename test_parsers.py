import sys, json
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).parent))
import vox, grand, sky
from normalize import merge, title_key

VOX_HTML = """
<html><body>
<a href="https://kwt.voxcinemas.com/movies/whatson">What's On</a>
<div><a href="https://kwt.voxcinemas.com/movies/moana"><img src="https://assets.voxcinemas.com/posters/P_1.jpg" alt="Movie poster for Moana"></a>
<h3><a href="https://kwt.voxcinemas.com/movies/moana">Moana</a></h3></div>
<div><h3><a href="https://kwt.voxcinemas.com/movies/moana-arabic">Moana</a></h3></div>
<div><h3><a href="https://kwt.voxcinemas.com/movies/siccin-9-turkish">Siccin 9</a></h3></div>
<div><h3><a href="https://kwt.voxcinemas.com/movies/the-furious">The Furious</a></h3></div>
</body></html>
"""

SKY_HTML = """
<html><body>
<img src="/images/movies/9999001455.jpg" title="MOANA - ENGLISH">
<h3>MOANA - ENGLISH</h3>
<a href="https://www.skycinemaskw.com/movie-information/moana-english/9999001455/NowShowing">MOVIE INFO</a>
<a href="https://www.skycinemaskw.com/movie-information/date-time-quantity/moana-english/9999001455/NowShowing">BOOK NOW</a>
<img src="/images/movies/9999001452.jpg" title="EBEN MEEN FEHOM (EGYPTIAN) - ARABIC">
<h3>EBEN MEEN FEHOM (EGYPTIAN) -...</h3>
<a href="https://www.skycinemaskw.com/movie-information/eben-meen-fehom-(egyptian)-arabic/9999001452/NowShowing">MOVIE INFO</a>
<h3>THE ODYSSEY</h3>
<a href="https://www.skycinemaskw.com/movie-information/the-odyssey/9999001361?c=y">MOVIE INFO</a>
<h3>MOANA - ENGLISH</h3>
<a href="https://www.skycinemaskw.com/movie-information/moana-english/9999001455/VIP">MOVIE INFO</a>
</body></html>
"""

GRAND_HTML = """
<html><body>
<a href="https://kw.grandcinemasme.com/movie/toy-story-5/en">Book Now</a>
<a href="https://kw.grandcinemasme.com/movie/the-furious/en">Book Now</a>
<a href="https://kw.grandcinemasme.com/movie/world-cup-games-the-final/en">Book Now</a>
<a href="https://kw.grandcinemasme.com/movie/spider-man-brand-new-day/en">Play Trailer</a>
<a href="https://kw.grandcinemasme.com/movie/moana/en">Book Now</a>
</body></html>
"""

def mock_get(html):
    r = MagicMock(); r.text = html; r.raise_for_status = lambda: None
    return lambda *a, **k: r

with patch("requests.get", mock_get(VOX_HTML)):
    v = vox.fetch()
assert len(v) == 4, v
assert v[0]["title_en"] == "Moana" and v[0]["language"] == "English"
assert v[1]["language"] == "Arabic"
assert v[2]["language"] == "Turkish"
print("vox ok")

with patch("requests.get", mock_get(SKY_HTML)):
    s = sky.fetch()
assert len(s) == 2, s
assert s[0]["title_en"] == "Moana" and s[0]["language"] == "English"
assert s[1]["title_en"] == "Eben Meen Fehom" and s[1]["language"] == "Arabic", s[1]
print("sky ok")

with patch("requests.get", mock_get(GRAND_HTML)):
    g = grand.fetch()
assert [m["title_en"] for m in g] == ["Toy Story 5", "The Furious", "Moana"], g
print("grand ok")

merged = merge({"vox": v, "sky": s, "grand": g})
moana = merged[title_key("Moana")]
assert {c["id"] for c in moana["cinemas"]} == {"vox", "sky", "grand"}, moana
assert set(moana["languages"]) == {"English", "Arabic"}
furious = merged[title_key("The Furious")]
assert {c["id"] for c in furious["cinemas"]} == {"vox", "grand"}
assert title_key("The Furious") == title_key("Furious")
assert title_key("(Arabic) Toy Story 5") == title_key("toy story 5")
print("merge ok")

import cinescape
CS_PAYLOAD = {"output": [
  {"id": "HO00004220", "title": "Moana", "titleAlt": "موانا", "language": "English",
   "synopsisAlt": "نسخة حية من فيلم موانا.", "genreAlt": "أكشن، كوميدي, مغامرات",
   "runTime": 115, "trailerUrl": "https://youtu.be/RrCjUcFfy48", "comingSoon": False,
   "webimgsmall": "https://cdn.cinescape.com.kw/movies/mob_small/HO00004220_058.jpg",
   "shareUrl": "https://www.cinescape.com.kw/moviesessions/moana/HO00004220"},
  {"id": "HO00009999", "title": "Future Movie", "comingSoon": True},
  {"id": "HO00004399", "title": "Eben Meen Fehom (Egyptian) - Arabic", "titleAlt": "ابن مين فيهم",
   "language": "Arabic", "genreAlt": "كوميدي", "runTime": 106,
   "trailerUrl": None, "comingSoon": False, "webimgsmall": None, "mobimgsmall": "x.jpg", "shareUrl": ""},
]}
def fake_post(url, json=None, headers=None, timeout=None):
    r = MagicMock(); r.raise_for_status = lambda: None
    r.json = lambda: CS_PAYLOAD
    return r
with patch("requests.post", fake_post):
    c = cinescape.fetch()
assert len(c) == 2, c
assert c[0]["trailer_youtube_id"] == "RrCjUcFfy48"
assert c[1]["poster_src"] == "x.jpg"
merged2 = merge({"vox": v, "sky": s, "cinescape": c})
k = title_key("Eben Meen Fehom (Egyptian) - Arabic")
assert k == title_key("Eben Meen Fehom")
e = merged2[k]
assert e["title_ar"] == "ابن مين فيهم" and e["runtime_min"] == 106
print("cinescape ok")
