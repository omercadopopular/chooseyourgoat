# Choose Your GOAT

An evidence-first football comparison interface. The six-player prototype includes Pelé, Lionel Messi, Cristiano Ronaldo, Ronaldo Nazário, Ronaldinho and Diego Maradona.

## Current status

The interface and metric engine are functional. The bundled observations are **illustrative fixture data**, designed to exercise filters, normalization, coverage display and chart behavior. They are not research-grade career records and must not be cited as such.

## Run locally

```bash
npm test
npx serve .
```

Open the address printed by `serve`.

## Product principles

- Compare players at a common age, appearance count or career season.
- Keep official matches and friendlies separate.
- Treat missing assists as unknown, never as zero.
- Display tournament wins as numerator and denominator.
- Make every eventual published statistic traceable to match and tournament-edition records.

See [docs/methodology.md](docs/methodology.md) and [docs/data-roadmap.md](docs/data-roadmap.md).

## Repository structure

- `index.html`, `styles.css`, `app.js`: dependency-free static application.
- `data/players.json`: prototype observations and coverage metadata.
- `src/metrics.js`: pure filter, normalization and comparison functions.
- `tests/metrics.test.js`: metric invariants.
- `scripts/validate-data.js`: schema and monotonicity checks.
- `.github/workflows/`: CI and GitHub Pages deployment.

## Data replacement contract

Each observation is a player-season-universe record. Production ingestion will replace these fixtures with match-level records and derive the same web schema. The UI must not require a rewrite when audited data arrive.

## License

Code is MIT licensed. The fixture data are synthetic and CC0. Future data snapshots may have different licenses and must pass a redistribution review before publication.

