# Choose Your GOAT

An evidence-first football comparison interface. The six-player prototype includes Pelé, Lionel Messi, Cristiano Ronaldo, Ronaldo Nazário, Ronaldinho and Diego Maradona.

## Current status

The interface and metric engine are functional. `data/players.json` remains an unmistakably labelled UI fixture. A separate reproducible research release now lives in `data/curated/`; it is not yet wired into the public chart while historical match-level coverage is incomplete.

## Run locally

```bash
npm test
npx serve .
```

Open the address printed by `serve`.

## Product principles

- Compare players at a common age, appearance count or career season.
- Never make “official” a data primitive; expose named competition families and let users select the universe.
- Keep national-team finals, qualifiers, intercontinental championships and friendlies separately selectable.
- Keep national leagues, continental club cups, intercontinental club cups, regional leagues and all other club matches separately selectable.
- Display tournament wins as numerator and denominator.
- Keep every published statistic traceable to a source row and disclose its granularity.

See [docs/methodology.md](docs/methodology.md) and [docs/data-roadmap.md](docs/data-roadmap.md).

## Repository structure

- `index.html`, `styles.css`, `app.js`: dependency-free static application.
- `data/players.json`: prototype observations and coverage metadata.
- `data/curated/`: sourced research tables, taxonomy, coverage and source manifest.
- `pipeline/`: downloader, extraction build and validation suite.
- `src/metrics.js`: pure filter, normalization and comparison functions.
- `tests/metrics.test.js`: metric invariants.
- `scripts/validate-data.js`: schema and monotonicity checks.
- `.github/workflows/`: CI and GitHub Pages deployment.

## Rebuild the research release

```bash
python -m pip install -r requirements.txt
python pipeline/download_public_sources.py
python pipeline/build_public_dataset.py
python pipeline/validate_public_dataset.py
```

The downloader caches raw inputs in ignored `data/raw/`. The curated tables retain source URLs and do not combine aggregates of different granularity.

## License

Code is MIT licensed. The UI fixture is synthetic and CC0. Curated rows have source-specific terms recorded in `data/curated/sources.csv`; RSSSF does not state an open redistribution license, so its factual extraction requires a terms review before commercial redistribution.
