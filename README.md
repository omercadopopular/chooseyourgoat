# Choose Your GOAT

An evidence-first football comparison interface covering Pelé, Lionel Messi, Cristiano Ronaldo, Ronaldo Nazário, Ronaldinho, Diego Maradona, Kylian Mbappé, Erling Haaland, Johan Cruyff, Roberto Baggio, Neymar, Robert Lewandowski, Luis Suárez, Ferenc Puskás and Romário.

## Current status

The public chart is wired to the reproducible research release through `data/web_dataset.json`. It provides independent hierarchical filters for the goals/games and competition-edition charts, normalization by age, appearances or career season, cumulative and marginal goal rates, and participation-confirmed title counts. The interface can be switched between English, Spanish and Brazilian Portuguese. The fixed comparison cutoff is 31 December 2025. All 15 competition ledgers have zero unmatched honours and zero unresolved aggregate rows; explicit evidence-based exclusions remain visible in the release metadata.

## Run locally

```bash
npm test
npx serve .
```

Open the address printed by `serve`.

## Product principles

- Compare players at a common age, appearance count or career season.
- Use named competition families and let users select the comparison universe.
- Keep youth national teams, senior finals, qualifiers, intercontinental championships and friendlies separately selectable in the goals chart; friendlies are omitted from the competition-edition selector.
- Keep lower-division clubs, top-flight national leagues, continental club cups, intercontinental club cups, regional leagues and all other club matches separately selectable.
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
python pipeline/expand_web_dataset.py
python pipeline/build_competition_editions.py
python pipeline/validate_public_dataset.py
npm run check
```

The downloader caches raw inputs in ignored `data/raw/`. The curated tables retain source URLs and do not combine aggregates of different granularity.

## License

Code is MIT licensed. Curated rows have source-specific terms recorded in `data/curated/sources.csv`; RSSSF does not state an open redistribution license, so its factual extraction requires a terms review before commercial redistribution.
