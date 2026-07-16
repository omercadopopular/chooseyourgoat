# Choose Your GOAT

An evidence-first football comparison interface. The six-player prototype includes Pelé, Lionel Messi, Cristiano Ronaldo, Ronaldo Nazário, Ronaldinho and Diego Maradona.

## Current status

The public chart is wired to the reproducible research release through `data/web_dataset.json`. It provides independent hierarchical filters for the goals/games and competition-edition charts, normalization by age, appearances or career season, cumulative and marginal goal rates, and participation-confirmed title counts. The fixed comparison cutoff is 31 December 2025.

## Run locally

```bash
npm test
npx serve .
```

Open the address printed by `serve`.

## Product principles

- Compare players at a common age, appearance count or career season.
- Use named competition families and let users select the comparison universe.
- Keep national-team finals, qualifiers, intercontinental championships and friendlies separately selectable.
- Keep national leagues, continental club cups, intercontinental club cups, regional leagues and all other club matches separately selectable.
- Keep title editions distinct from individual awards and runner-up finishes.
- Keep every published statistic traceable to a source row and disclose its granularity.

See [docs/methodology.md](docs/methodology.md) and [docs/data-roadmap.md](docs/data-roadmap.md).

## Repository structure

- `index.html`, `styles.css`, `app.js`: dependency-free static application.
- `data/web_dataset.json`: generated, coverage-aware browser bundle.
- `data/players.json`: retained legacy fixture; no longer loaded by the website.
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

Code is MIT licensed. Curated rows have source-specific terms recorded in `data/curated/sources.csv`; RSSSF does not state an open redistribution license, so its factual extraction requires a terms review before commercial redistribution.
