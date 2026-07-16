import { readFile } from "node:fs/promises";

const data = JSON.parse(await readFile(new URL("../data/web_dataset.json", import.meta.url)));
const errors = [];
const base = ["pele", "messi", "cristiano", "ronaldo", "ronaldinho", "maradona"];
const expansion = ["mbappe", "haaland", "cruyff", "baggio", "neymar", "lewandowski", "suarez", "puskas", "romario"];
const buckets = new Set(data.taxonomy.flatMap(group => group.children.map(child => child.id)));

if (data.meta.isFixture !== false) errors.push("web dataset is marked as a fixture");
if (data.meta.dataCutoff !== "2025-12-31") errors.push("unexpected data cutoff");
const ids = data.players.map(player => player.id);
if (JSON.stringify(ids.slice(0, 6)) !== JSON.stringify(base)) errors.push("canonical six-player roster mismatch");
if (![6, 15].includes(ids.length)) errors.push("player expansion must be all-or-none");
if (ids.length === 15 && JSON.stringify(ids.slice(6)) !== JSON.stringify(expansion)) errors.push("nine-player expansion roster mismatch");

for (const player of data.players) {
  if (!player.observations.length) errors.push(`${player.id}: no observations`);
  for (const row of player.observations) {
    if (!buckets.has(row.bucket)) errors.push(`${player.id}: unknown bucket ${row.bucket}`);
    if (row.appearances < 0 || row.goals < 0) errors.push(`${player.id}: negative observation`);
    if (row.goals > row.appearances * 6) errors.push(`${player.id}: implausible goal ratio`);
  }
  for (const title of player.titles) if (!buckets.has(title.bucket)) errors.push(`${player.id}: unknown title bucket ${title.bucket}`);
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}

console.log(`Validated ${data.players.length} players, ${data.players.reduce((sum, player) => sum + player.observations.length, 0)} web observations and ${data.players.reduce((sum, player) => sum + player.titles.length, 0)} titles.`);
