"""Development-only routes. Mounted only when the dev mock provider is enabled."""
from fastapi import APIRouter, HTTPException, Response

from app.providers.mock_dev import is_known_track, tone_wav

router = APIRouter(prefix="/dev", tags=["dev"], include_in_schema=False)


@router.get("/mock-audio/{track_id}.wav")
def mock_audio(track_id: str) -> Response:
    if not is_known_track(track_id):
        raise HTTPException(404, "Unknown sample track")
    return Response(tone_wav(track_id), media_type="audio/wav", headers={"Cache-Control": "max-age=3600"})
