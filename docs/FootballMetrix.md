# BallScope — Phased Build Roadmap

**Context date:** July 6, 2026. The 2026 World Cup is already in the knockout rounds (Round of 16 → Quarterfinals), with the final on July 19. Only ~8 matches remain in the real tournament. This matters a lot for sequencing — see the note at the end of Phase 0.

**Scope note:** this is an end-to-end MLOps pipeline, not a web app with a model bolted on. Experiment tracking, data versioning, a model registry with promotion gates, and CI/CD for retraining are load-bearing parts of the plan below, not a bonus phase at the end — they're folded into Phases 0, 2, 3, and 6.

---

## Phase 0 — Foundation & Data Reality Check
**Goal:** De-risk the two hardest parts (data sourcing, model training data) before writing any UI.

**Do:**
- Lock the monorepo structure: `apps/frontend`, `apps/backend`, `ml/`, `infra/` (Docker Compose for Postgres + Redis).
- Write the Alembic migrations for the 13 core tables (`teams`, `matches`, `historical_matches`, `players`, `player_stats`, `team_stats`, `engineered_features`, `predictions`, `prediction_results`, `model_versions`, `model_metrics`, `data_source_logs`, `cache_metadata`).
- Source a **historical dataset** to train on — this is the actual bottleneck, not the frontend. Realistic option: Kaggle's "International football results from 1872 to 2026" (or equivalent), supplemented with FBref for advanced stats (xG, possession) where scraping is feasible.
- Do an honest audit of the "potential sources" list — see table below. Pick 2–3 real ones, don't plan around all 8.
- Set up the MLOps scaffolding alongside the app scaffolding: `dvc init` for versioning the historical dataset and engineered-features artifacts, an MLflow tracking server (SQLite-backed is fine for a solo project) for experiment logging, and separate Dockerfiles for the training pipeline vs the serving API — training and serving have different dependency footprints and shouldn't share an image.

**Data source reality check:**

| Source | Reality |
|---|---|
| FIFA | No public API. Skip as a live source; useful only for reference stats you hardcode/seed. |
| FBref | No API, but structured HTML tables are scrape-friendly for historical stats. Good for training data, not real-time. |
| Transfermarkt | Scraping is common in the community but fragile and against ToS — use sparingly, cache heavily, don't depend on it live. |
| Sofascore / FotMob | No public API; scraping is actively fought (frequent structure changes). Treat as "nice to have," not a dependency. |
| Football-Data / API-Football (RapidAPI) | Actual public API with WC coverage on paid tiers. This is your most realistic **live** source. |
| Odds API (the-odds-api.com) | Real, keyed, reliable — good for the odds-comparison angle. |
| OpenWeather | Real, trivial to integrate, no caveats. |

**Decision to make now:** injuries/lineups/tactical data have no clean free API. You'll either (a) semi-manually curate these for the remaining ~8 teams as a "premium curated data" story, or (b) simplify those features into lower-fidelity heuristics (e.g., squad depth from rosters, not real-time injury feeds). Decide which honestly — don't let this quietly block Phase 4.

**Timeline note — read before Phase 1:** With the real WC2026 down to knockout rounds, a "select any two remaining teams" live predictor has a shelf life of about two weeks before the tournament ends and the demo goes stale. Two options, not mutually exclusive:
1. **Ship a WC2026 knockout-round demo now** using the real remaining fixtures (great narrative for a portfolio: "predicted the 2026 World Cup live").
2. **Architect team/competition selection as data-driven, not WC-hardcoded**, so after July 19 you can point the same engine at any league (Premier League 2026–27 season starts in August) and the project stays alive as a working product instead of freezing on July 19. Strongly recommend doing this from the start — it costs little now and saves a rewrite later.

---

## Phase 1 — MVP Walking Skeleton
**Goal:** One full request/response loop working end to end, even with a crude model.

- Landing page + team selector, pulling from a seeded `teams` table (real remaining WC teams).
- `/predict` endpoint: fetch seeded features → run a simple baseline (logistic regression or Elo-difference heuristic) → return probabilities.
- Prediction loading screen with the animated pipeline text.
- Dashboard sections: **Feature 1** (Prediction Summary), **Feature 2** (Probability Distribution), **Feature 3** (Expected Scorelines via basic Poisson).
- No live scraping yet, no Monte Carlo yet, no SHAP yet — this phase proves the pipes work.

**Exit criterion:** you can pick two teams and see a real (if simplistic) dashboard render in under a few seconds.

---

## Phase 2 — Real Prediction Engine (Tracked & Reproducible)
**Goal:** Replace the baseline with the actual ML stack described in the spec, built as a tracked pipeline from the first training run — not instrumented after the fact.

- Feature engineering from historical data: ELO ratings, rolling form (last 5/10 matches), head-to-head record, home/neutral venue effect. Version the resulting `engineered_features` artifact with DVC, tied to the git commit that produced it.
- Train XGBoost for win/draw/loss classification; validate with proper train/test splits by season (not random splits — avoid leakage across time). Log every run — hyperparameters, metrics, SHAP summary, dataset version — to MLflow, so you can compare runs instead of overwriting your only result.
- Poisson model for expected goals → scoreline distribution.
- Monte Carlo simulation (10k runs) layered on the Poisson model.
- SHAP integration → **Feature 10** (Feature Importance) and **Feature 17** (Explainability Panel).
- Model registry with a promotion gate: a new model version only becomes "production" in `model_versions` if it beats the current production model on held-out accuracy/log loss/Brier score; otherwise it's logged but not promoted. This gate is what turns Feature 20 (Phase 6) into a real evaluation story rather than a dashboard with no teeth.

**Exit criterion:** predictions are backed by a real trained model with explainable output, benchmarked against a naive baseline (e.g., "always predict the higher-ELO team") so you can show it's actually better — and every run that produced it is reproducible from a logged commit + data version.

---

## Phase 3 — Live Data Integration
**Goal:** Wire in the 2–3 real APIs chosen in Phase 0, with Redis doing its job.

- Integrate API-Football (or equivalent) for live stats, Odds API for market odds, OpenWeather for conditions.
- Redis caching layer with sensible TTLs; log every fetch to `data_source_logs`.
- **Feature 16** (Data Sources health cards) — this one is almost free once logging exists.
- Decide and implement your Phase-0 injuries/lineups approach (curated vs heuristic).
- Wire the retraining trigger: when a real result lands, append it to the DVC-versioned dataset as a new revision and queue a retrain rather than running it synchronously in the request path. The actual retrain job runs in Phase 6's CI/CD pipeline — this phase just makes sure new results are captured and versioned, not lost.

---

## Phase 4 — Analytical Depth
**Goal:** The features that make the dashboard feel like a real analytics product rather than a single prediction card.

- **Feature 6** Team Comparison radar chart.
- **Feature 8** Player Spotlight (driven by whatever player_stats you actually have — xG/xA if available, otherwise goals/assists as a fallback, stated honestly in the UI).
- **Feature 9** Momentum trend graphs (form, goals, xG over recent matches).
- **Feature 7** Squad Health.
- **Feature 5** Tactical Analysis — be upfront that true tactical modeling (formation detection, press intensity) is a research problem; a defensible v1 is a rules-based summary from formation/style tags you curate per team, not something XGBoost outputs. Don't oversell this one in the UI copy.

---

## Phase 5 — Trust & Meta-Prediction Layer
**Goal:** The features that build user trust in the number, not just show it.

- **Feature 11** Monte Carlo visualization (animated distribution of the 10k simulated outcomes).
- **Feature 12** Prediction Confidence (model agreement across XGBoost/Poisson, data completeness score).
- **Feature 13** Upset Meter.
- **Feature 15** Prediction Timeline — requires a scheduled job (cron / Celery beat) that re-runs predictions periodically and snapshots them; can't be built as a one-off endpoint.
- **Feature 14** Latest Updates feed, sourced from whatever news/injury pipeline you built in Phase 3.

---

## Phase 6 — CI/CD, Monitoring & Model Ops
**Goal:** Close the loop — this is the phase that actually makes it an MLOps pipeline rather than a one-time training script.

- **CI/CD retraining pipeline** (GitHub Actions): on a schedule (e.g., after each matchday) or on new-data trigger from Phase 3, pull the latest DVC data revision, retrain, evaluate against the held-out set, and apply the Phase 2 promotion gate. If the new model wins, promote it to production and log the version; if not, log the run and leave production untouched — no silent auto-deploys of a worse model.
- **Drift monitoring:** track rolling live-prediction accuracy against the backtested accuracy from training time; if they diverge past a threshold, flag it (log entry at minimum, alert if you want to take it further). This is what tells you the model is going stale before your users do.
- **Feature 19** Prediction Archive (this should already be populating from Phase 1 onward if `predictions` is written on every call — just needs a UI).
- **Feature 18** PDF export.
- **Feature 20** Model Performance Dashboard: accuracy, log loss, Brier score, calibration curve, confusion matrix, accuracy by confidence bucket, **plus model version history from the registry** so this page visibly reflects the promotion gate above rather than just describing one static model. Backtest against historical completed matches (from your Phase 0 dataset) so the dashboard has real numbers before any 2026 predictions have resolved.

---

## Phase 7 — Design & Deployment Polish
**Goal:** Make it look like Opta/Bloomberg, not a hackathon project.

- Apply the dark, minimal, restrained-animation aesthetic throughout (per the spec's design language section).
- Framer Motion pass on transitions, not just the loading screen.
- Deploy: frontend on Vercel, backend on Railway/Render, managed Postgres (Supabase, matching your other projects) + Redis (Upstash).
- Load test the `/predict` path — this is the one endpoint that fans out to multiple APIs + a Monte Carlo sim, so it's the latency risk.

---

## Suggested Sequencing Priority (if time-boxed)

If you only get through part of this before the WC2026 window closes on July 19, the highest-leverage cut is **Phase 0 → 1 → 2 → 3**, plus a minimal slice of Phase 6 — the MLflow tracking, DVC-versioned data, and the promotion-gated model registry, even without the full GitHub Actions automation — plus **Feature 6 (radar)** and **Feature 20 (model performance)**. That combination demonstrates real ML + real data + a real MLOps loop + honest evaluation, which is the substance recruiters actually probe on. The full CI/CD automation, drift monitoring, and remaining dashboard features are depth and polish that can continue after the tournament ends, especially once you generalize past WC2026 per the Phase 0 note.
