import { readFile } from "node:fs/promises";

const data = JSON.parse(await readFile(new URL("../data/web_dataset.json", import.meta.url)));
const errors = [];
const base = ["pele", "messi", "cristiano", "ronaldo", "ronaldinho", "maradona"];
const expansion = ["mbappe", "haaland", "cruyff", "baggio", "neymar", "lewandowski", "suarez", "puskas", "romario"];
const expansionNationalTotals = { mbappe:[94,55], haaland:[48,55], cruyff:[48,33], baggio:[56,27], neymar:[128,79], lewandowski:[163,88], suarez:[143,69], puskas:[89,84], romario:[70,55] };
const partialClubTotals = { cristiano:[15,14], mbappe:[24,29], haaland:[24,25], lewandowski:[18,8] };
const buckets = new Set(data.taxonomy.flatMap(group => group.children.map(child => child.id)));

if (data.meta.isFixture !== false) errors.push("web dataset is marked as a fixture");
if (data.meta.dataCutoff !== "2025-12-31") errors.push("unexpected data cutoff");
const ids = data.players.map(player => player.id);
if (JSON.stringify(ids.slice(0, 6)) !== JSON.stringify(base)) errors.push("canonical six-player roster mismatch");
if (ids.length !== 15) errors.push("published bundle must contain all 15 players");
if (JSON.stringify(ids.slice(6)) !== JSON.stringify(expansion)) errors.push("nine-player expansion roster mismatch");

for (const player of data.players) {
  if (!player.observations.length) errors.push(`${player.id}: no observations`);
  for (const row of player.observations) {
    if (!buckets.has(row.bucket)) errors.push(`${player.id}: unknown bucket ${row.bucket}`);
    if (row.appearances < 0 || row.goals < 0) errors.push(`${player.id}: negative observation`);
    if (row.goals > row.appearances * 6) errors.push(`${player.id}: implausible goal ratio`);
  }
  for (const title of player.titles) if (!buckets.has(title.bucket)) errors.push(`${player.id}: unknown title bucket ${title.bucket}`);
  const editionIds=player.competitions.map(row=>row.edition_id);
  if (new Set(editionIds).size!==editionIds.length) errors.push(`${player.id}: duplicate canonical competition-edition ID`);
  if (player.competitionCoverage.honoursUnmatched!==0) errors.push(`${player.id}: unmatched honours remain`);
  const complete=player.competitionCoverage.honoursUnmatched===0&&player.competitionCoverage.unresolvedAggregateRows.length===0;
  if ((player.competitionCoverage.reconciliationStatus==="complete")!==complete) errors.push(`${player.id}: incorrect reconciliation status`);
  if (partialClubTotals[player.id]) {
    const rows=player.observations.filter(row=>row.source_granularity==="partial_season_from_match_ledger");
    const actual=[rows.reduce((sum,row)=>sum+row.appearances,0),rows.reduce((sum,row)=>sum+row.goals,0)];
    if (JSON.stringify(actual)!==JSON.stringify(partialClubTotals[player.id])) errors.push(`${player.id}: 2025 partial ledger reconciles to ${actual.join("/")}`);
  }
  if (expansionNationalTotals[player.id]) {
    const rows = player.observations.filter(row => row.team_context === "national_team");
    const actual = [rows.reduce((sum,row)=>sum+row.appearances,0), rows.reduce((sum,row)=>sum+row.goals,0)];
    if (JSON.stringify(actual) !== JSON.stringify(expansionNationalTotals[player.id])) errors.push(`${player.id}: national ledger reconciles to ${actual.join("/")}`);
    if (new Set(rows.map(row=>row.bucket)).size < 2) errors.push(`${player.id}: national matches are not allocated by type`);
  }
}

if (![...buckets].includes("lower_division_club") || ![...buckets].includes("national_team_youth")) errors.push("missing youth/lower-division selector buckets");

const haalandCity = data.players.find(player=>player.id==="haaland").observations.filter(row=>row.team==="Manchester City");
if (haalandCity.reduce((sum,row)=>sum+row.appearances,0)!==170 || haalandCity.reduce((sum,row)=>sum+row.goals,0)!==149) errors.push("haaland: Manchester City ledger must reconcile to 170 appearances/149 goals at cutoff");

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}

console.log(`Validated ${data.players.length} players, ${data.players.reduce((sum, player) => sum + player.observations.length, 0)} web observations and ${data.players.reduce((sum, player) => sum + player.titles.length, 0)} titles.`);
