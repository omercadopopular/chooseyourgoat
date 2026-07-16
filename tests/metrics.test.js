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

test("all 15 requested players exist", () => {
  assert.deepEqual(players.map(player => player.id), ["pele", "messi", "cristiano", "ronaldo", "ronaldinho", "maradona", "mbappe", "haaland", "cruyff", "baggio", "neymar", "lewandowski", "suarez", "puskas", "romario"]);
});

test("hierarchy contains every requested user bucket", () => {
  assert.deepEqual(groups.club, ["national_league", "continental_federation_cup", "intercontinental_federation_cup", "regional_league", "all_other_club"]);
  assert.ok(groups.national_team.includes("national_team_intercontinental_championship_finals"));
  assert.ok(groups.national_team.includes("national_team_friendlies"));
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
    assert.ok(player.competitions.every(edition => edition.appearances > 0 || edition.bench_listings > 0));
    for (const metric of ["cumulativeCompetitionWinRate"]) {
      const series=buildCompetitionSeries(player,{metric,axis:"competitionCount",buckets:allBuckets});
      assert.ok(series.every(point => point.y >= 0 && point.y <= 1));
    }
  }
});

test("friendlies never count as competition editions", () => {
  for (const player of players) assert.ok(player.competitions.every(edition => edition.bucket !== "national_team_friendlies" && edition.competition_family !== "club_friendly"));
});
