"""Stage 1: scrape all cinemas -> merge -> data/raw_listings.json"""
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import vox, grand, sky, cinescape  # noqa: E402
from normalize import merge  # noqa: E402

SOURCES = {"vox": vox, "grand": grand, "sky": sky, "cinescape": cinescape}
OUT = Path(__file__).parent / "data" / "raw_listings.json"


def main():
    listings, failures = {}, []
    for cinema_id, module in SOURCES.items():
        try:
            items = module.fetch()
            listings[cinema_id] = items
            print(f"[{cinema_id}] {len(items)} listings")
        except Exception:
            failures.append(cinema_id)
            print(f"[{cinema_id}] FAILED:\n{traceback.format_exc()}")

    merged = merge(listings)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "failures": failures,
        "movies": merged,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(merged)} unique movies -> {OUT}")
    if failures:
        print(f"WARNING: failed sources: {failures}")
        sys.exit(1)


if __name__ == "__main__":
    main()
