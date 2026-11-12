"""Serve the built Vite SPA from FastAPI in production (single origin for the PWA).

Looks for `frontend/dist` (or FRONTEND_DIST). API routers stay authoritative for
`/api/*`. Audio streams are never part of the SPA static tree.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import REPO_ROOT

log = logging.getLogger(__name__)

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


def mount_spa(app: FastAPI) -> bool:
    root = resolve_dist()
    if root is None:
        log.info("SPA dist not found — API-only mode")
        return False

    assets = root / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="spa-assets")

    @app.get("/", include_in_schema=False)
    async def spa_index():
        return FileResponse(root / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # Never steal API (or docs) — those routers are registered first and match first,
        # but guard anyway for clarity.
        if full_path.startswith("api/") or full_path in {"docs", "redoc", "openapi.json"}:
            raise HTTPException(404, "Not found")
        name = full_path.strip("/")
        if name in _PUBLIC:
            candidate = root / name
            if candidate.is_file():
                headers = {}
                if name == "sw.js":
                    headers["Cache-Control"] = "no-cache"
                    headers["Service-Worker-Allowed"] = "/"
                return FileResponse(candidate, headers=headers)
        # Missing hashed asset → 404 (don't return HTML as JS).
        if name.startswith("assets/"):
            raise HTTPException(404, "Not found")
        return FileResponse(root / "index.html")

    log.info("Serving SPA from %s", root)
    return True
