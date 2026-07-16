export const metricLabels = {
  goals: "Cumulative goals",
  goalsPerGame: "Cumulative average goals / game",
  marginalGoalsPerGame: "Marginal average goals / game",
  titles: "Cumulative titles won"
};

export const competitionMetricLabels = {
  competitionsWon: "Cumulative competitions won",
  cumulativeCompetitionWinRate: "Cumulative average win rate"
};

const dayMs = 86_400_000;

function ageAtYearEnd(born, year) {
  return +((Date.parse(`${year}-12-31`) - Date.parse(born)) / dayMs / 365.2425).toFixed(2);
}

export function buildSeries(player, { metric = "goals", axis = "age", buckets = [] } = {}) {
  const selected = new Set(buckets);
  // Multi-year aggregates have no defensible position on an age/year curve.
  // Plotting them at the span endpoint manufactures a one-year jump.
  const observations = player.observations.filter(row => selected.has(row.bucket) && !row.aggregate_only);
  const titles = player.titles.filter(row => selected.has(row.bucket));
  const allYears = [...player.observations.map(row => +row.period_end.slice(0, 4)), ...player.titles.map(row => row.year)];
  const careerStart = Math.min(...allYears);
  const byYear = new Map();
  for (const row of observations) {
    const year = +row.period_end.slice(0, 4);
    const value = byYear.get(year) || { year, appearances: 0, goals: 0, titles: 0 };
    value.appearances += row.appearances;
    value.goals += row.goals;
    byYear.set(year, value);
  }
  for (const title of titles) {
    const value = byYear.get(title.year) || { year: title.year, appearances: 0, goals: 0, titles: 0 };
    value.titles += 1;
    byYear.set(title.year, value);
  }
  let appearances = 0, goals = 0, titleCount = 0;
  return [...byYear.values()].sort((a, b) => a.year - b.year).map(row => {
    appearances += row.appearances;
    goals += row.goals;
    titleCount += row.titles;
    const age = ageAtYearEnd(player.born, row.year);
    const careerSeason = row.year - careerStart + 1;
    const values = {
      goals,
      goalsPerGame: appearances ? goals / appearances : null,
      marginalGoalsPerGame: row.appearances ? row.goals / row.appearances : null,
      titles: titleCount
    };
    const x = axis === "appearances" ? appearances : axis === "careerSeason" ? careerSeason : age;
    return { x, y: values[metric], year: row.year, age, careerSeason, appearances, goals, titles: titleCount, periodAppearances: row.appearances, periodGoals: row.goals };
  }).filter(point => point.x >= 0 && point.y !== null && (metric === "titles" || point.appearances > 0));
}

export function buildCompetitionSeries(player, { metric = "competitionsWon", axis = "competitionCount", buckets = [] } = {}) {
  const selected=new Set(buckets); const byYear=new Map();
  for(const edition of player.competitions||[]){
    if(!selected.has(edition.bucket)) continue;
    const row=byYear.get(edition.year)||{year:edition.year,played:0,won:0};
    row.played+=1; row.won+=edition.won?1:0; byYear.set(edition.year,row);
  }
  let played=0,won=0;
  return [...byYear.values()].sort((a,b)=>a.year-b.year).map(row=>{
    played+=row.played; won+=row.won;
    const age=ageAtYearEnd(player.born,row.year);
    const values={competitionsWon:won,cumulativeCompetitionWinRate:played?won/played:null};
    return {x:axis==="age"?age:played,y:values[metric],year:row.year,age,played,won,periodPlayed:row.played,periodWon:row.won};
  }).filter(p=>p.y!==null);
}

export function commonEndpoint(seriesList) {
  const populated = seriesList.filter(series => series.length);
  if (!populated.length) return null;
  return Math.min(...populated.map(series => Math.max(...series.map(point => point.x))));
}

export function trimToCommon(seriesList) {
  const endpoint = commonEndpoint(seriesList);
  return endpoint == null ? seriesList : seriesList.map(series => series.filter(point => point.x <= endpoint));
}

export function lastAtOrBefore(series, endpoint) {
  return [...series].reverse().find(point => point.x <= endpoint) || series[0];
}

export function formatMetric(value, metric) {
  if (value == null) return "N/A";
  if (["goalsPerGame", "marginalGoalsPerGame"].includes(metric)) return value.toFixed(2);
  if (metric === "cumulativeCompetitionWinRate") return `${(value*100).toFixed(1)}%`;
  return Math.round(value).toLocaleString("en-US");
}
