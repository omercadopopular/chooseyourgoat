# Data roadmap

## What the first research release covers

- All six players have club season-by-competition aggregates and dated senior
  national-team goal events.
- All six have complete RSSSF senior national-team appearance ledgers through
  31 December 2025: 800 appearances and 464 goals, fully reconciled.
- Messi and Cristiano Ronaldo have CC0 match-level appearances, goals, minutes,
  opponents and results from 2012 in the current snapshot.
- All six have championship-edition honour lists with runner-up and individual
  awards excluded.
- RSSSF's broad Pelé universe is retained as a parallel 1,413-match, 1,324-goal
  aggregate assertion, including 451 Santos friendlies with 449 goals and 43
  Cosmos friendlies with 29 goals. It is not silently added to the finer season
  table because the sources overlap.

## Material gaps

1. Historical club friendlies, tours, benefit matches and other games are not
   yet enumerated match by match. Pelé's broader RSSSF totals are captured, but
   their dates and opponents are still absent for most of the 494 club
   friendlies in that assertion.
2. Match-level appearances and wins before 2012 remain incomplete for all six;
   the CC0 structured supplement covers only Messi and Cristiano in this set.
3. Season tables sometimes expose broad source buckets (“Other”, “Competitive”)
   that cannot be allocated to a named competition without match ledgers.
4. Honours lists do not independently prove edition participation.
5. RSSSF pages are excellent reconciliation references but do not state an open
   redistribution license. Commercial publication needs a terms review or
   independently reconstructed facts from match sheets and open archives.

## Next ingestion order

1. Build Pelé’s club match ledger, including friendlies and tours, preserving
   each source treatment and dispute rather than collapsing to one total.
2. Extend Maradona, Ronaldo Nazário and Ronaldinho club match ledgers from RSSSF,
   club archives and contemporary match sheets.
3. Backfill Messi and Cristiano before 2012 and reconcile the structured feed
   against club and federation season totals.
4. Link appearances to competition editions to calculate entered/won shares.

## Release gate for the public charts

The interface is now coverage-aware and loads sourced records. It states that
club age curves use season endpoints, while national-team inputs originate in
match ledgers. Win-rate views remain disabled for mixed club/national universes
until historical club results are complete.
