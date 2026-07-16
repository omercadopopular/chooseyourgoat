import { readFile } from "node:fs/promises";

const data = JSON.parse(await readFile(new URL("../data/players.json", import.meta.url)));
const errors = [];
const ids = new Set();
if (!data.meta?.isFixture) errors.push("Prototype data must retain isFixture=true until audited replacement.");
if (data.players?.length !== 6) errors.push("Expected exactly six prototype players.");

for (const player of data.players ?? []) {
  if (ids.has(player.id)) errors.push(`Duplicate player id: ${player.id}`);
  ids.add(player.id);
  if (!player.name || !player.country || !Number.isFinite(player.startAge)) errors.push(`Incomplete identity: ${player.id}`);
  if (!/^#[0-9a-f]{6}$/i.test(player.color)) errors.push(`Invalid color: ${player.id}`);
  for (const [index, row] of player.seasons.entries()) {
    if (!Array.isArray(row) || row.length !== 8) errors.push(`${player.id} season ${index + 1}: expected eight fields`);
    if (row.some(value => !Number.isInteger(value) || value < 0)) errors.push(`${player.id} season ${index + 1}: values must be nonnegative integers`);
    const [apps, goals, assists, wins, tournaments, clubTournaments, clubWeight, won] = row;
    if (wins > apps) errors.push(`${player.id} season ${index + 1}: wins exceed appearances`);
    if (clubTournaments > tournaments || won > tournaments) errors.push(`${player.id} season ${index + 1}: invalid tournament counts`);
    if (clubWeight < 1 || clubWeight > 5) errors.push(`${player.id} season ${index + 1}: club allocation weight outside 1–5`);
    if (goals > apps * 2 || assists > apps * 2) errors.push(`${player.id} season ${index + 1}: implausible fixture rate`);
  }
  for (const key of ["goals", "results", "assists"]) if (player.coverage[key] < 0 || player.coverage[key] > 100) errors.push(`${player.id}: invalid ${key} coverage`);
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
console.log(`Validated ${data.players.length} players and ${data.players.reduce((n,p)=>n+p.seasons.length,0)} season fixtures.`);
