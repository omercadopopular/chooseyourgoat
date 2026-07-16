export const metricLabels = {
  goals: "Cumulative goals",
  goalsPerGame: "Cumulative goals / game",
  winShare: "Match win share",
  trophyShare: "Tournament win share"
};

const sum = (rows, key) => rows.reduce((total, row) => total + row[key], 0);

export function expandPlayer(player) {
  const keys = ["appearances", "goals", "assists", "wins", "tournaments", "clubTournaments", "clubWeight", "tournamentsWon"];
  return player.seasons.map((tuple, index) => ({
    ...Object.fromEntries(keys.map((key, i) => [key, tuple[i]])),
    careerSeason: index + 1,
    age: +(player.startAge + index).toFixed(1)
  }));
}

function applyUniverse(row, universe) {
  if (universe === "all") return row;
  const clubShare = Math.min(0.9, Math.max(0.7, 0.65 + row.clubWeight * 0.05));
  const share = universe === "club" ? clubShare : 1 - clubShare;
  return {
    ...row,
    appearances: Math.round(row.appearances * share),
    goals: Math.round(row.goals * (universe === "club" ? share : Math.min(0.45, share + 0.08))),
    assists: Math.round(row.assists * share),
    wins: Math.round(row.wins * share),
    tournaments: universe === "club" ? row.clubTournaments : row.tournaments - row.clubTournaments,
    tournamentsWon: Math.min(universe === "club" ? row.tournamentsWon : Math.round(row.tournamentsWon * .35), universe === "club" ? row.clubTournaments : row.tournaments - row.clubTournaments)
  };
}

export function buildSeries(player, { metric = "goals", axis = "age", universe = "all" } = {}) {
  const rows = expandPlayer(player).map(row => applyUniverse(row, universe));
  return rows.map((row, index) => {
    const history = rows.slice(0, index + 1);
    const appearances = sum(history, "appearances");
    const goals = sum(history, "goals");
    const assists = sum(history, "assists");
    const wins = sum(history, "wins");
    const tournaments = sum(history, "tournaments");
    const tournamentsWon = sum(history, "tournamentsWon");
    const values = {
      goals,
      goalsPerGame: appearances ? goals / appearances : null,
      assists,
      winShare: appearances ? wins / appearances : null,
      trophyShare: tournaments ? tournamentsWon / tournaments : null
    };
    return { x: axis === "appearances" ? appearances : row[axis], y: values[metric], appearances, goals, assists, wins, tournaments, tournamentsWon, age: row.age, careerSeason: row.careerSeason };
  }).filter(point => point.x > 0 && point.y !== null);
}

export function commonEndpoint(seriesList) {
  if (!seriesList.length) return null;
  return Math.min(...seriesList.map(series => Math.max(...series.map(point => point.x))));
}

export function trimToCommon(seriesList) {
  const endpoint = commonEndpoint(seriesList);
  return seriesList.map(series => series.filter(point => point.x <= endpoint));
}

export function lastAtOrBefore(series, endpoint) {
  return [...series].reverse().find(point => point.x <= endpoint) || series[0];
}

export function formatMetric(value, metric) {
  if (value == null) return "N/A";
  if (["winShare", "trophyShare"].includes(metric)) return `${(value * 100).toFixed(1)}%`;
  if (metric === "goalsPerGame") return value.toFixed(2);
  return Math.round(value).toLocaleString("en-US");
}
