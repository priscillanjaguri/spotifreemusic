"""Live check of the Audius adapter. Run from backend/:  python -m scripts.check_audius [query]"""
import sys

from app.core.config import get_settings
from app.providers.audius import AudiusAdapter

settings = get_settings()
if not settings.audius_configured:
    sys.exit("Audius is disabled. Set AUDIUS_ENABLED=true (default) with AUDIUS_API_HOST / AUDIUS_APP_NAME.")

query = sys.argv[1] if len(sys.argv) > 1 else "lofi"
adapter = AudiusAdapter(
    api_host=settings.audius_api_host,
    app_name=settings.audius_app_name,
    api_key=settings.audius_api_key,
)
tracks = adapter.search_tracks(query, limit=5)
print(f"query={query!r} results={len(tracks)}")
for t in tracks:
    artists = ", ".join(a.name for a in t.artists)
    print(f"- {t.title} · {artists} · {t.duration_ms}ms · {t.stream_url}")
if not tracks:
    sys.exit("No streamable Audius tracks returned.")
