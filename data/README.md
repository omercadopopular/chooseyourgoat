# Data status

The production research data are generated into `data/curated/` by
`pipeline/build_public_dataset.py`.

Every observation is classified by team context, competition family, format,
seniority and source treatment. Users choose the comparison universe.

## Current public sources

- Wikipedia career-statistics, international-goal and honours tables, licensed
  under CC BY-SA. These tables consolidate citations to clubs, federations,
  RSSSF and specialist databases.
- RSSSF chronological international records, used directly for the canonical
  six senior national-team appearance ledgers and the broad Pelé reconciliation.
- Public career-statistics and honours tables for the nine-player expansion.
  Club seasons are career-spanning. Complete senior national-team match ledgers
  come from RSSSF for seven players and Transfermarkt's public performance feed
  for Mbappé and Haaland; every cap is allocated by competition family before
  being grouped for the browser chart.
- Public Transfermarkt performance ledgers provide the dated post-table 2025
  segments for Cristiano Ronaldo, Mbappé, Haaland and Lewandowski, and
  appearance evidence for modern honour reconciliation.
- `dcaribou/transfermarkt-datasets`, CC0, used for match-level Messi and
  Cristiano Ronaldo coverage from 2012 onward.

## Output tables

- `season_competition.csv`: player-season-source-bucket appearances and goals.
- `national_team_goal_events.csv`: dated national-team goals with competition
  taxonomy.
- `national_team_appearances.csv`: complete senior national-team RSSSF ledgers
  for the canonical six through 31 December 2025. Every cap and goal reconciles.
- `national_team_appearances_rsssf.csv`: compatibility extract containing the
  91-row Maradona portion of the unified appearance table.
- `modern_match_appearances.csv`: modern match-level appearances, results and
  goals where the structured source has coverage.
- `historical_aggregate_assertions.csv`: parallel multi-year source assertions,
  currently RSSSF's broad Pelé set (1,413 matches, 1,324 goals). These overlap
  finer tables and cannot support exact-age curves.
- `titles.csv`: championship editions listed in player honours, excluding
  runner-up and individual awards.
- `coverage.json`: source coverage by player.
- `competition_taxonomy.csv`: machine-readable selectable families and their
  mapping to the user-facing buckets.
- `sources.csv`: provenance, retrieval date, license/terms and caveats.
- `../web_dataset.json`: generated browser bundle used by the live chart; it
  contains only non-overlapping observations, a named participation-confirmed
  competition-edition ledger, and the selectable hierarchy.

These tables are a research release, not a claim of perfect completeness.
Every row retains its source and granularity. Competition names and team aliases
are canonicalized before edition IDs are constructed. A player's reconciliation
is labelled complete only when no unmatched honour or unresolved aggregate row
remains; unsupported honours are disclosed and excluded from win counts.

Do not add aggregate rows from `season_competition.csv` to match-level rows.
They are alternative views with overlapping coverage. In particular, the
historical season table has broad career coverage but does not enumerate all
club friendlies and tours; the modern match table is richer but only covers
  Messi and Cristiano Ronaldo from 2012 while they remain covered by the
  source competitions. It ends in 2023 and 2022 respectively and is not their
  complete modern career record.
