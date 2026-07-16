import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { buildSeries, commonEndpoint, formatMetric, trimToCommon } from "../src/metrics.js";

const fixture = JSON.parse(await readFile(new URL("../data/players.json", import.meta.url)));
const players = fixture.players;

test("fixture is unmistakably marked as non-production", () => {
  assert.equal(fixture.meta.isFixture, true);
  assert.match(fixture.meta.notice, /not verified/i);
});

test("all six requested players exist", () => {
  assert.deepEqual(players.map(p => p.id), ["pele", "messi", "cristiano", "ronaldo", "ronaldinho", "maradona"]);
});

test("cumulative counts never decrease", () => {
  for (const player of players) {
    for (const metric of ["goals", "assists"]) {
      const series = buildSeries(player, { metric, axis: "careerSeason", universe: "official" });
      series.slice(1).forEach((point, i) => assert.ok(point.y >= series[i].y, `${player.id} ${metric}`));
    }
  }
});

test("common support trims every series to a shared endpoint", () => {
  const raw = players.slice(0, 3).map(player => buildSeries(player, { metric: "goals", axis: "careerSeason" }));
  const endpoint = commonEndpoint(raw);
  const trimmed = trimToCommon(raw);
  assert.equal(endpoint, 22);
  trimmed.forEach(series => assert.ok(Math.max(...series.map(p => p.x)) <= endpoint));
});

test("club and national universes partition appearances approximately", () => {
  for (const player of players) {
    const official = buildSeries(player, { metric: "goals", axis: "careerSeason", universe: "official" }).at(-1).appearances;
    const club = buildSeries(player, { metric: "goals", axis: "careerSeason", universe: "club" }).at(-1).appearances;
    const national = buildSeries(player, { metric: "goals", axis: "careerSeason", universe: "national" }).at(-1).appearances;
    assert.ok(Math.abs(official - club - national) <= player.seasons.length);
  }
});

test("shares format as percentages", () => {
  assert.equal(formatMetric(.375, "trophyShare"), "37.5%");
  assert.equal(formatMetric(null, "assists"), "N/A");
});

