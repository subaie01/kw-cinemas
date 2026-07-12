# سينما الكويت — Kuwait Cinemas Aggregator

All movies now showing in Kuwait cinemas (Cinescape, VOX, Grand, Sky) in one JSON file, updated automatically every day. No accounts or API keys needed anywhere.

## How it works

- `main.py` scrapes the 4 cinema sites → `data/raw_listings.json`
- `enrich.py` adds Arabic metadata + ratings from keyless public sources (Wikidata, official IMDb datasets, Arabic Wikipedia, and Cinescape's own Arabic data) → `data/movies.json`
- `.github/workflows/daily.yml` runs both every morning and commits the result
- The app/website read `data/movies.json` from this repo's CDN URL

## Manual fixes

Edit `overrides.json` to pin a Wikidata match, correct an Arabic title/synopsis, or set an exact YouTube trailer per movie. Cached movies live in `data/cache/` — add `"refresh": true` to an override to re-fetch one.

## Run locally

```
pip install -r requirements.txt
python main.py && python enrich.py
python test_parsers.py && python test_enrich.py
```
