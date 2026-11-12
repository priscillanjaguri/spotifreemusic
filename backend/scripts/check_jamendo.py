"""Live check of the Jamendo adapter. Run from backend/:  python -m scripts.check_jamendo [query]"""
import sys

from app.core.config import get_settings
from app.providers.jamendo import JamendoAdapter

client_id = get_settings().jamendo_client_id
if not client_id:
    sys.exit("JAMENDO_CLIENT_ID is not set in .env")

query = sys.argv[1] if len(sys.argv) > 1 else "chill"
tracks = JamendoAdapter(client_id).search_tracks(query, limit=5)
print(f"{len(tracks)} tracks for '{query}'")
for t in tracks:
    print(f"- {t.title} / {', '.join(a.name for a in t.artists)} | genres={t.genres} | "
          f"stream={'yes' if t.stream_url else 'NO'} | licence={t.license_url}")
