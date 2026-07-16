# Data status

The production research data are generated into `data/curated/` by
`pipeline/build_public_dataset.py`.

The model does not contain an `official` flag. Every observation is classified
by team context, competition family, format, seniority and source treatment.
Users choose the comparison universe.

## Current public sources

- Wikipedia career-statistics, international-goal and honours tables, licensed
  under CC BY-SA. These tables consolidate citations to clubs, federations,
  RSSSF and specialist databases.
- RSSSF chronological international records, currently used directly for
  Maradona and as a reconciliation source for the other five players.
- `dcaribou/transfermarkt-datasets`, CC0, used for match-level Messi and
  Cristiano Ronaldo coverage from 2012 onward.

## Output tables

- `season_competition.csv`: player-season-source-bucket appearances and goals.
- `national_team_goal_events.csv`: dated national-team goals with competition
  taxonomy.
- `national_team_appearances_rsssf.csv`: the 91-row Maradona national-team
  appearance ledger; its 34 goals reconcile to the goal-event table.
- `modern_match_appearances.csv`: modern match-level appearances, results and
  goals where the structured source has coverage.
- `titles.csv`: championship editions listed in player honours, excluding
  runner-up and individual awards.
- `coverage.json`: source coverage by player.
- `competition_taxonomy.csv`: machine-readable selectable families and their
  mapping to the user-facing buckets.
- `sources.csv`: provenance, retrieval date, license/terms and caveats.

These tables are a research release, not a claim of perfect completeness.
Every row retains its source and granularity.

Do not add aggregate rows from `season_competition.csv` to match-level rows.
They are alternative views with overlapping coverage. In particular, the
historical season table has broad career coverage but does not enumerate all
club friendlies and tours; the modern match table is richer but only covers
Messi and Cristiano Ronaldo from 2012 in the current CC0 snapshot.
