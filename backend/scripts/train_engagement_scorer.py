#!/usr/bin/env python3
"""Offline / cron entrypoint: train the engagement scorer from labeled impressions.

Usage (from repo root, with DATABASE_URL set):

    python -m scripts.train_engagement_scorer
    python -m scripts.train_engagement_scorer --no-activate

Or hit the secret-gated API (same EVAL_RUN_SECRET as /eval/run):

    curl -X POST https://HOST/api/v1/scorer/retrain \\
      -H "X-Eval-Secret: $EVAL_RUN_SECRET" -H "Content-Type: application/json" \\
      -d '{"activate": true}'
"""
from __future__ import annotations

import argparse
import sys

from app.core.db import SessionLocal
from app.services import scorer_job


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train Spotifree engagement scorer")
    parser.add_argument(
        "--no-activate",
        action="store_true",
        help="Save the model without marking it active",
    )
    args = parser.parse_args(argv)

    db = SessionLocal()
    try:
        result = scorer_job.retrain(db, activate=not args.no_activate)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(result.message)
    if result.metrics:
        print("metrics:", result.metrics)
    # Non-zero when training did not activate (cold start / imbalance) so cron can alert.
    if not result.activated:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
