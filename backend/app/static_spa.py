"""Serve the built Vite SPA from FastAPI in production (single origin for the PWA).

Looks for `frontend/dist` (or FRONTEND_DIST). API routers stay authoritative for
`/api/*`. Audio streams are never part of the SPA static tree.
"""
from __future__ import annotations

import logging
import mimetypes
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import REPO_ROOT

log = logging.getLogger(__name__)

# Ensure webp is recognized even if the host mime db is thin.
mimetypes.add_type("image/webp", ".webp")

_PUBLIC = (
    "manifest.webmanifest",
    "sw.js",
    "favicon.svg",
    "icon-192.png",
    "icon-512.png",
    "icon-512-maskable.png",
    "apple-touch-icon.png",
)


def resolve_dist() -> Path | None:
    env = os.environ.get("FRONTEND_DIST", "").strip()
    root = Path(env).expanduser() if env else REPO_ROOT / "frontend" / "dist"
    if root.is_dir() and (root / "index.html").is_file():
        return root
    return None


def _safe_file(root: Path, relative: str) -> Path | None:
    """Return an existing file under root, or None (blocks path traversal)."""
    name = relative.strip("/")
    if not name or ".." in Path(name).parts:
        return None
    candidate = (root / name).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def mount_spa(app: FastAPI) -> bool:
    root = resolve_dist()
    if root is None:
        log.info("SPA dist not found — API-only mode")
        return False

    assets = root / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="spa-assets")

    # Inspiration / mood photos live in public/mood → dist/mood. Mount explicitly
    # so /mood/*.webp is never swallowed by the SPA HTML fallback.
    mood = root / "mood"
    if mood.is_dir():
        app.mount("/mood", StaticFiles(directory=mood), name="spa-mood")

    _html_headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
    }

    @app.get("/", include_in_schema=False)
    async def spa_index():
        # Always revalidate the shell so new hashed JS/CSS ship after deploys.
        return FileResponse(root / "index.html", headers=_html_headers)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # Never steal API (or docs) — those routers are registered first and match first,
        # but guard anyway for clarity.
        if full_path.startswith("api/") or full_path in {"docs", "redoc", "openapi.json"}:
            raise HTTPException(404, "Not found")
        name = full_path.strip("/")
        # Missing hashed asset → 404 (don't return HTML as JS).
        if name.startswith("assets/") or name.startswith("mood/"):
            raise HTTPException(404, "Not found")

        # Root-level public files (icons, SW, manifest) and any other real dist file.
        if name in _PUBLIC or "." in Path(name).name:
            candidate = _safe_file(root, name)
            if candidate is not None:
                headers: dict[str, str] = {}
                if name == "sw.js":
                    headers["Cache-Control"] = "no-cache"
                    headers["Service-Worker-Allowed"] = "/"
                return FileResponse(candidate, headers=headers)

        return FileResponse(root / "index.html", headers=_html_headers)

    log.info("Serving SPA from %s (mood=%s)", root, mood.is_dir())
    return True
