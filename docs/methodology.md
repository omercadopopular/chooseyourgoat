# Methodology

## Unit of comparison

The product compares documented football records through user-selected named
competition families. Every record has a team context, named competition, mapped
competition family, seniority, source, and source granularity. Users construct
their comparison universe by selecting families.

The national-team choices are World Cup finals, World Cup qualification,
continental championship finals, continental championship qualification,
intercontinental championship finals, continental Nations League, Olympic,
friendlies, and other. “Intercontinental championship finals” includes the FIFA
Confederations Cup, Finalissima, Artemio Franchi Cup, and comparable senior
competitions between continental champions.

The club choices are national league, continental federation cup,
intercontinental federation cup, regional league, and all other club matches.
Domestic cups and super cups are retained internally and roll up to “all other”
unless the interface exposes the finer controls.

## Metrics

- Goals per game = selected goals / selected appearances.
- Marginal average goals per game = goals in the current dated observation
  period / appearances in that period. The period is a season for historical
  club aggregates and a calendar year for the national-team ledger.
- Cumulative average goals per game = all selected goals through the plotted
  point / all selected appearances through that point.
- Cumulative rate at appearance *n* = goals through appearance *n* / *n*.
- Cumulative rate by age is plotted at calendar-year or season endpoints in the
  six-player web bundle. The underlying national ledger retains exact dates;
  historical club aggregates cannot support match-by-match age curves.
- Cumulative titles = selected championship editions listed in the honours
  source through that age or career season.

Penalty-shootout kicks are not player goals. A match result retains regulation
or extra-time W/D/L separately from shootout advancement when the source offers
both. Own goals are not attributed to the compared player.

## Titles

The current `titles.csv` records championship editions listed in public player
honours. Runner-up finishes and individual awards are excluded. A competition
edition is counted as played only when the player has a documented appearance
or is named on the bench. The current denominator is appearance-confirmed; the
schema separately records bench listings as lineup sources become available.
Friendlies and tours are excluded. A win enters the numerator only when a
participated edition reconciles to the player's honours. Unmatched honours are
reported as coverage gaps and excluded.

- Cumulative average win rate = editions won through the point / editions
  played through the point.

## Common support

When normalizing by age, appearances, or career season, the default chart ends
at the greatest point observed for every selected player under the same filters.
Users may opt into full-career lines, but unmatched tails must be visually
marked.

## Provenance and uncertainty

Season aggregates, goal events, appearance ledgers, and title lists are not
summed merely because they share a player. They overlap and represent different
views. The generated web bundle combines non-overlapping club aggregates,
senior national-team ledgers, and youth/Olympic aggregates. Pelé's explicitly
documented assertions reconcile the detailed table to RSSSF's broader
1,413-match/1,324-goal universe and are marked `aggregate_only`. They remain in
the dataset for provenance and career-total reconciliation, but are excluded
from timelines because RSSSF does not allocate those multi-year totals by date
or season. Assigning them to the last year of the span would create a fictitious
1974 jump. Every canonical output row retains a URL and granularity.

For the plotted Pelé “all other club goals” curve, Santos friendly and tour
matches are allocated by calendar year using the public match-by-match ledger
at `pt.wikipedia.org/wiki/Estatísticas_de_Pelé`. Its Santos friendly series has
450 matches and 449 goals from 1956–1974. The separate RSSSF 451/449 aggregate
is retained as a source assertion, not added to this series, because the two
records overlap and differ by one appearance.
