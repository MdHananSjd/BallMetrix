---
name: tournament-generalization
description: Design patterns and database schemas to generalize the match prediction system to support any football tournament or league without hardcoding.
---

# Tournament & League Generalization

This skill ensures that all schemas, data collection services, and ML models can dynamically support any football competition.

## Database Schema Structure
Avoid assuming a single tournament. All tables that store match-related or team-related statistics must be grouped or filtered by a `competition_id` and a `season`.

1. **Competitions Table**:
   - `id` (primary key, e.g., string like `PL` or integer)
   - `name` (e.g., "English Premier League", "FIFA World Cup")
   - `type` (e.g., "league", "cup", "tournament")
   - `country` (e.g., "England", "International")

2. **Teams / Competition Mapping**:
   - Teams are not hardcoded. A many-to-many relationship `competition_teams` (`competition_id`, `team_id`, `season`) maps team participation.

3. **Matches & Historical Matches**:
   - Include `competition_id` and `season` (e.g., `2026`).
   - Include `stage` or `round` (e.g., `Group Stage`, `Round of 16`, `Matchday 3`).

4. **Predictions & Features**:
   - Ensure the `predictions` table references `competition_id`.
   - Feature engineering (e.g., Elo, rolling form) should be partitioned by `competition_id` or calculated globally across all matches but filtered by competition when predicting.

## API Sourcing Generalization
- The backend API client must abstract the third-party providers (e.g. API-Football).
- Query parameters in endpoints (like `/predict` or `/matches`) must take a `competition_id` and `season` instead of assuming hardcoded World Cup tournament codes.
- Map the internal `competition_id` to the provider's corresponding competition code (e.g. API-Football's `league_id` for World Cup is `1`, Premier League is `39`).

## ML Model Handling
- The feature engineering pipeline must generate features such as team Elo or form from general historical match datasets.
- Ensure validation splits are based on time/season across all competitions, avoiding hardcoded tournament dates.
