# Methodology

## Unit of comparison

The product compares documented football records, not a source-imposed class
called “official.” Every record has a team context, named competition, mapped
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
- Marginal season rate = goals in that season / appearances in that season.
- Cumulative rate at appearance *n* = goals through appearance *n* / *n*.
- Cumulative rate by age uses exact match dates where available. A season-level
  source cannot support exact age curves and must be labelled as approximate or
  omitted from that view.
- Match win share = selected appearances in team wins / selected appearances.
- Tournament win share = entered-and-won editions / entered editions.

Penalty-shootout kicks are not player goals. A match result retains regulation
or extra-time W/D/L separately from shootout advancement when the source offers
both. Own goals are not attributed to the compared player.

## Titles

The current `titles.csv` records championship editions listed in public player
honours. Runner-up finishes and individual awards are excluded. The field
`participation_status=listed_in_player_honours` is deliberately cautious: it
does not assert that the player appeared in that edition. A later match-level
edition ledger should add at least `squad_member`, `appeared_in_edition`, and
`appeared_in_final` as separate facts.

## Common support

When normalizing by age, appearances, or career season, the default chart ends
at the greatest point observed for every selected player under the same filters.
Users may opt into full-career lines, but unmatched tails must be visually
marked.

## Provenance and uncertainty

Season aggregates, goal events, appearance ledgers, and title lists are never
summed merely because they share a player. They overlap and represent different
views. Every output row retains a URL and granularity. Conflicting sources
should be stored as parallel assertions with a discrepancy identifier and a
written explanation, not silently resolved.
