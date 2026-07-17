import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { buildCompetitionSeries, buildSeries, commonEndpoint, formatMetric, trimToCommon } from "../src/metrics.js";

const data = JSON.parse(await readFile(new URL("../data/web_dataset.json", import.meta.url)));
const players = data.players;
const groups = Object.fromEntries(data.taxonomy.map(group => [group.id, group.children.map(child => child.id)]));
const allBuckets = Object.values(groups).flat();

test("research bundle has a fixed cutoff and is not a fixture", () => {
  assert.equal(data.meta.isFixture, false);
  assert.equal(data.meta.dataCutoff, "2025-12-31");
});

test("the complete 15-player roster is published", () => {
  const base = ["pele", "messi", "cristiano", "ronaldo", "ronaldinho", "maradona"];
  const expansion = ["mbappe", "haaland", "cruyff", "baggio", "neymar", "lewandowski", "suarez", "puskas", "romario"];
  assert.deepEqual(players.slice(0, 6).map(player => player.id), base);
  assert.equal(players.length, 15);
  assert.deepEqual(players.slice(6).map(player => player.id), expansion);
});

test("hierarchy contains every requested user bucket", () => {
  assert.deepEqual(groups.club, ["national_league", "lower_division_club", "continental_federation_cup", "intercontinental_federation_cup", "regional_league", "all_other_club"]);
  assert.ok(groups.national_team.includes("national_team_intercontinental_championship_finals"));
  assert.ok(groups.national_team.includes("national_team_youth"));
  assert.ok(groups.national_team.includes("national_team_friendlies"));
});

test("lower-division clubs and youth national teams are separately populated", () => {
  assert.ok(players.some(player => player.observations.some(row => row.bucket === "lower_division_club")));
  assert.ok(players.some(player => player.observations.some(row => row.bucket === "national_team_youth")));
  assert.ok(players.find(player => player.id === "messi").observations.some(row => row.team === "Barcelona B" && row.bucket === "lower_division_club"));
});

test("cumulative goals and titles never decrease", () => {
  for (const player of players) {
    for (const metric of ["goals", "titles"]) {
      const series = buildSeries(player, { metric, axis: "careerSeason", buckets: allBuckets });
      series.slice(1).forEach((point, index) => assert.ok(point.y >= series[index].y, `${player.id} ${metric}`));
    }
  }
});

test("club and national filters partition the web observations", () => {
  for (const player of players) {
    const all = buildSeries(player, { metric: "goals", axis: "careerSeason", buckets: allBuckets }).at(-1);
    const club = buildSeries(player, { metric: "goals", axis: "careerSeason", buckets: groups.club }).at(-1);
    const national = buildSeries(player, { metric: "goals", axis: "careerSeason", buckets: groups.national_team }).at(-1);
    assert.equal(all.goals, club.goals + national.goals);
    assert.equal(all.appearances, club.appearances + national.appearances);
  }
});

test("expansion national ledgers reconcile and are allocated by type", () => {
  const expected = {
    mbappe: [94, 55], haaland: [48, 55], cruyff: [48, 33],
    baggio: [56, 27], neymar: [128, 79], lewandowski: [163, 88],
    suarez: [143, 69], puskas: [89, 84], romario: [70, 55]
  };
  for (const [id, totals] of Object.entries(expected)) {
    const rows = players.find(player => player.id === id).observations.filter(row => row.team_context === "national_team");
    assert.deepEqual([rows.reduce((sum, row) => sum + row.appearances, 0), rows.reduce((sum, row) => sum + row.goals, 0)], totals, id);
    assert.ok(new Set(rows.map(row => row.bucket)).size >= 2, `${id}: national matches remain unallocated`);
    assert.ok(rows.every(row => row.bucket !== "national_team_all_matches_unallocated"), `${id}: unallocated national total`);
  }
});

test("Europe club columns are classified as continental federation cups", () => {
  for (const player of players.slice(6)) {
    const rows = player.observations.filter(row => row.team_context === "club" && row.competition_name.toLowerCase() === "europe");
    assert.ok(rows.every(row => row.bucket === "continental_federation_cup"), player.id);
  }
});

test("Haaland includes the dated 2025-26 segment through the cutoff", () => {
  const haaland = players.find(player => player.id === "haaland");
  const city = haaland.observations.filter(row => row.team === "Manchester City");
  assert.deepEqual(
    [city.reduce((sum,row)=>sum+row.appearances,0), city.reduce((sum,row)=>sum+row.goals,0)],
    [170,149]
  );
  const partial = city.filter(row => row.source_granularity === "partial_season_from_match_ledger");
  assert.deepEqual(
    [partial.reduce((sum,row)=>sum+row.appearances,0), partial.reduce((sum,row)=>sum+row.goals,0)],
    [24,25]
  );
});

test("all four partial 2025 club ledgers reconcile without season overlap", () => {
  const expected = { cristiano:[15,14], mbappe:[24,29], haaland:[24,25], lewandowski:[18,8] };
  for (const [id, totals] of Object.entries(expected)) {
    const partial=players.find(player=>player.id===id).observations.filter(row=>row.source_granularity==="partial_season_from_match_ledger");
    assert.deepEqual([partial.reduce((sum,row)=>sum+row.appearances,0),partial.reduce((sum,row)=>sum+row.goals,0)],totals,id);
    assert.ok(partial.every(row=>row.first_date>="2025-07-01" && row.last_date<="2025-12-31"),id);
  }
});

test("Pelé's multi-year aggregate assertions are not plotted at 1974", () => {
  const pele = players.find(player => player.id === "pele");
  const otherClub = buildSeries(pele, { metric: "goals", axis: "careerSeason", buckets: ["all_other_club"] });
  const point1974 = otherClub.find(point => point.year === 1974);
  const point1973 = otherClub.find(point => point.year === 1973);
  assert.ok(!point1974 || !point1973 || point1974.goals - point1973.goals < 100);
  assert.ok(pele.observations.some(row => row.aggregate_only && row.goals === 449));
  const allocated = pele.observations.filter(row => row.team === "Santos" && row.competition_family === "club_friendly");
  assert.equal(allocated.reduce((sum, row) => sum + row.goals, 0), 448);
  assert.equal(allocated.find(row => row.period === "1974").goals, 4);
});

test("common support trims every populated series", () => {
  const raw = players.slice(0, 3).map(player => buildSeries(player, { metric: "goals", axis: "age", buckets: allBuckets }));
  const endpoint = commonEndpoint(raw);
  trimToCommon(raw).forEach(series => assert.ok(Math.max(...series.map(point => point.x)) <= endpoint));
});

test("rates format with two decimal places", () => {
  assert.equal(formatMetric(.375, "goalsPerGame"), "0.38");
  assert.equal(formatMetric(null, "goalsPerGame"), "N/A");
});

test("competition editions require participation and win rates are bounded", () => {
  for (const player of players) {
    assert.ok(player.competitions.length > 0);
    assert.ok(player.competitions.every(edition => edition.participation_confirmed || edition.appearances > 0 || edition.bench_listings > 0));
    for (const metric of ["cumulativeCompetitionWinRate"]) {
      const series=buildCompetitionSeries(player,{metric,axis:"competitionCount",buckets:allBuckets});
      assert.ok(series.every(point => point.y >= 0 && point.y <= 1));
    }
    assert.equal(new Set(player.competitions.map(edition=>edition.edition_id)).size,player.competitions.length,`${player.id}: duplicate canonical edition ID`);
    assert.equal(player.competitionCoverage.honoursUnmatched,0,`${player.id}: unmatched honour`);
    const fullyReconciled=player.competitionCoverage.honoursUnmatched===0&&player.competitionCoverage.unresolvedAggregateRows.length===0;
    assert.equal(player.competitionCoverage.reconciliationStatus==="complete",fullyReconciled,`${player.id}: reconciliation status`);
  }
});

test("competition-name aliases merge before edition counting", () => {
  const cristiano=players.find(player=>player.id==="cristiano");
  const euro2024=cristiano.competitions.filter(row=>row.edition_id==="national|portugal|europeanchampionship|2024");
  assert.equal(euro2024.length,1);
  assert.equal(euro2024[0].appearances,5);
  const ronaldo=players.find(player=>player.id==="ronaldo");
  const confed1997=ronaldo.competitions.filter(row=>row.edition_id==="national|brazil|confederationscup|1997");
  assert.equal(confed1997.length,1);
  assert.equal(confed1997[0].appearances,5);
});

test("Pelé's competition ledger reconciles to 28 wins from 64 played editions", () => {
  const pele=players.find(player=>player.id==="pele");
  assert.equal(pele.competitions.length,64);
  assert.equal(pele.competitions.filter(edition=>edition.won).length,28);
  const series=buildCompetitionSeries(pele,{metric:"cumulativeCompetitionWinRate",axis:"competitionCount",buckets:allBuckets});
  assert.equal(series.at(-1).played,64);
  assert.equal(series.at(-1).won,28);
  assert.equal(series.at(-1).y,28/64);
});

test("friendlies never count as competition editions", () => {
  for (const player of players) assert.ok(player.competitions.every(edition => edition.bucket !== "national_team_friendlies" && edition.competition_family !== "club_friendly" && !/friendl|tour matches/i.test(edition.competition_name)),player.id);
});

test("friendlies are omitted from the competition-edition selector", async () => {
  const app=await readFile(new URL("../app.js",import.meta.url),"utf8");
  assert.match(app,/child\.id !== "national_team_friendlies"/);
});

test("competition editions use named competitions rather than aggregate columns", () => {
  const forbidden = new Set(["national cup", "continental", "europe", "other", "cup", "league", "postseason", "competitive", "friendly", "state league", "regional league", "league cup"]);
  for (const player of players) assert.ok(player.competitions.every(edition => !forbidden.has(edition.competition_name.toLowerCase())));
});
