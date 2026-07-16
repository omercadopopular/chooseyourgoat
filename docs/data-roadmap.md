# Data roadmap

## What the first research release covers

- All six players have club season-by-competition aggregates and dated senior
  national-team goal events.
- Maradona has a complete 91-appearance RSSSF national-team ledger.
- Messi and Cristiano Ronaldo have CC0 match-level appearances, goals, minutes,
  opponents and results from 2012 in the current snapshot.
- All six have championship-edition honour lists with runner-up and individual
  awards excluded.

## Material gaps

1. Historical club friendlies, tours, benefit matches and other games are not
   yet enumerated match by match. This is especially consequential for Pelé.
2. Match-level appearances and wins before 2012 remain incomplete for all six;
   the CC0 structured supplement covers only Messi and Cristiano in this set.
3. Season tables sometimes expose broad source buckets (“Other”, “Competitive”)
   that cannot be allocated to a named competition without match ledgers.
4. Honours lists do not independently prove edition participation.
5. RSSSF pages are excellent reconciliation references but do not state an open
   redistribution license. Commercial publication needs a terms review or
   independently reconstructed facts from match sheets and open archives.

## Next ingestion order

1. Build full senior national-team appearance ledgers for the other five from
   federation/RSSSF lists, then reconcile every dated goal.
2. Build Pelé’s club match ledger, including friendlies and tours, preserving
   each source treatment and dispute rather than collapsing to one total.
3. Extend Maradona, Ronaldo Nazário and Ronaldinho club match ledgers from RSSSF,
   club archives and contemporary match sheets.
4. Backfill Messi and Cristiano before 2012 and reconcile the structured feed
   against club and federation season totals.
5. Link appearances to competition editions to calculate entered/won shares.

## Release gate for the public charts

The fixture warning should remain until the interface becomes coverage-aware.
Each plotted metric must declare whether its denominator is match-level,
season-level, or title-list coverage and must disable exact-age or win-rate views
when the required match dates/results are absent.
