#!/usr/bin/env python3
"""Offline / cron entrypoint: train the sequential next-track model from listening.

Usage (from backend/, with DATABASE_URL set):

    python -m scripts.train_sequential
    python -m scripts.train_sequential --no-activate

Or hit the secret-gated API (same EVAL_RUN_SECRET as /eval/run):

    curl -X POST https://HOST/api/v1/sequential/retrain \\
      -H "X-Eval-Secret: $EVAL_RUN_SECRET" -H "Content-Type: application/json" \\
      -d '{"activate": true}'
"""
from __future__ import annotations

import argparse
import sys

from app.core.db import SessionLocal
from app.services import sequential_job


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train Spotifree sequential next-track model")
    parser.add_argument(
        "--no-activate",
        action="store_true",
        help="Save the model without marking it active",
    )
    args = parser.parse_args(argv)

    db = SessionLocal()
    try:
        result = sequential_job.retrain(db, activate=not args.no_activate)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(result.message)
    if result.metrics:
        print("metrics:", result.metrics)
    if not result.activated:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
