# Testing Spotifree

## Backend (pytest)

Uses a **separate** Postgres database (`TEST_DATABASE_URL`). Migrations run from a blank schema each
session, so tests also verify Alembic + Postgres-only constraints (`btree_gist` exclusion).

```bash
cd backend
source .venv/bin/activate
pytest                          # full suite
pytest tests/test_e2e_flow.py   # Stage 7 product flow
pytest tests/test_analytics.py tests/test_companion.py
pytest -k listening             # filter by name
```

### What the e2e flow covers
`tests/test_e2e_flow.py` walks:

1. Register / `/auth/me`
2. Provider search → add to collection
3. Preferences (seed genres + timezone)
4. Post listening events (player segments)
5. Feedback (like)
6. Recommendations + similar tracks
7. Weekly analytics, taste timeline, memory lane
8. Daily companion (mood)
9. Delete listening history (likes/saves survive)

### Offline recommender metrics
```bash
python -m scripts.eval_recommender
```

## Frontend

```bash
cd frontend
npm run typecheck
npm run build
```

There is no headless browser suite yet. Product UI is verified manually (or via agent screenshots)
against a running stack with `DEV_MOCK_PROVIDER=true` when no Jamendo key is set:

1. Register → Home shows For You / Companion / Analytics teasers
2. Discover → play a track → player posts `/listening/events`
3. Analytics → weekly stats, taste timeline, memory lane; toggle privacy / delete history
4. Companion → pick a mood → playlist + insights
5. My Library → upload a generated tone → play alongside Jamendo/mock tracks
6. For You → like / not interested → list updates

## Manual smoke checklist (Stage 7)

| Step | Expect |
|---|---|
| Auth register/login | Cookie session; redirect to Home |
| Search + save | Collection grows; facets update |
| Play ≥ 1s | `POST /listening/events` 201 (or null body if history off) |
| Like a track | Feedback 200; appears in taste milestones |
| `/recommendations` | Non-empty picks after seeds/likes |
| `/analytics` | Listening time / tops when events exist |
| `/companion` | Briefing + playlist; mood POST refreshes |
| Delete history | Analytics zeros; collection/likes remain |
| Typecheck + pytest | Clean |

Legal test audio only: generated tones (`scripts/make_test_audio.py`) or Jamendo CC with
`audiodownload_allowed`. Never commit `.env` or real secrets.
