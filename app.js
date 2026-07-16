import { buildSeries, commonEndpoint, formatMetric, lastAtOrBefore, metricLabels, trimToCommon } from "./src/metrics.js";

const data = await fetch("./data/players.json").then(response => response.json());
const state = { selected: new Set(["pele", "messi", "cristiano"]), metric: "goals", axis: "age", universe: "official", common: true };
const $ = selector => document.querySelector(selector);
const playerGrid = $("#player-grid");
const colors = Object.fromEntries(data.players.map(player => [player.id, player.color]));

function renderPlayers() {
  playerGrid.innerHTML = data.players.map((player, index) => `
    <button class="player-card ${state.selected.has(player.id) ? "selected" : ""}" data-id="${player.id}" aria-pressed="${state.selected.has(player.id)}">
      <span class="number">0${index + 1}</span><span class="check">${state.selected.has(player.id) ? "●" : "○"}</span>
      <strong>${player.shortName}</strong><small>${player.country} · ${player.years}</small>
    </button>`).join("");
  playerGrid.querySelectorAll("button").forEach(button => button.addEventListener("click", () => {
    const id = button.dataset.id;
    if (state.selected.has(id) && state.selected.size > 2) state.selected.delete(id);
    else if (!state.selected.has(id) && state.selected.size < 4) state.selected.add(id);
    render();
  }));
}

function linePath(points, xScale, yScale) { return points.map((p, i) => `${i ? "L" : "M"}${xScale(p.x).toFixed(1)},${yScale(p.y).toFixed(1)}`).join(" "); }

function renderChart() {
  const selectedPlayers = data.players.filter(player => state.selected.has(player.id));
  let series = selectedPlayers.map(player => buildSeries(player, state));
  const endpoint = commonEndpoint(series);
  if (state.common) series = trimToCommon(series);
  const all = series.flat();
  const xMin = Math.min(...all.map(p => p.x)); const xMax = Math.max(...all.map(p => p.x));
  const yMin = state.metric.includes("Share") || state.metric === "goalsPerGame" ? 0 : Math.min(0, ...all.map(p => p.y));
  const yMax = Math.max(...all.map(p => p.y)) * 1.08 || 1;
  const W = 1000, H = 420, pad = {l:58,r:25,t:18,b:42};
  const x = value => pad.l + (value-xMin)/(xMax-xMin || 1)*(W-pad.l-pad.r);
  const y = value => H-pad.b-(value-yMin)/(yMax-yMin || 1)*(H-pad.t-pad.b);
  const ticks = Array.from({length:6}, (_,i)=>({v:yMin+(yMax-yMin)*i/5, py:y(yMin+(yMax-yMin)*i/5)}));
  const xTicks = Array.from({length:6}, (_,i)=>xMin+(xMax-xMin)*i/5);
  const paths = series.map((points, i) => `<path class="series" stroke="${selectedPlayers[i].color}" d="${linePath(points,x,y)}"/>${points.map((p,j)=>`<circle class="point" tabindex="0" data-player="${selectedPlayers[i].shortName}" data-x="${p.x}" data-y="${p.y}" cx="${x(p.x)}" cy="${y(p.y)}" r="${j===points.length-1?5:3.5}" fill="${selectedPlayers[i].color}"/>`).join("")}`).join("");
  $("#chart").innerHTML = `<svg viewBox="0 0 ${W} ${H}" aria-hidden="true">${ticks.map(t=>`<line class="gridline" x1="${pad.l}" x2="${W-pad.r}" y1="${t.py}" y2="${t.py}"/><text class="axis-label" x="${pad.l-10}" y="${t.py+3}" text-anchor="end">${formatMetric(t.v,state.metric)}</text>`).join("")}${xTicks.map(v=>`<text class="axis-label" x="${x(v)}" y="${H-12}" text-anchor="middle">${state.axis==="age"?v.toFixed(0):Math.round(v)}</text>`).join("")}${paths}</svg>`;
  $("#chart-kicker").textContent = metricLabels[state.metric].toUpperCase();
  $("#chart-title").textContent = `By ${state.axis === "careerSeason" ? "career season" : state.axis}`;
  $("#legend").innerHTML = selectedPlayers.map(p=>`<span class="legend-item"><i class="dot" style="background:${p.color}"></i>${p.shortName}</span>`).join("");
  $("#support-note").textContent = state.common ? `Common endpoint: ${state.axis === "age" ? endpoint.toFixed(1) : Math.round(endpoint)} ${state.axis}` : "Full available fixture careers shown";
  $("#chart").querySelectorAll(".point").forEach(point => {
    const show = event => { const tip=$("#tooltip"); tip.hidden=false; tip.innerHTML=`<strong>${point.dataset.player}</strong>${state.axis}: ${Number(point.dataset.x).toFixed(state.axis==="age"?1:0)}<br>${metricLabels[state.metric]}: ${formatMetric(Number(point.dataset.y),state.metric)}`; tip.style.left=`${Math.min(innerWidth-180,event.clientX+12)}px`;tip.style.top=`${Math.max(8,event.clientY-62)}px`; };
    point.addEventListener("pointerenter",show);point.addEventListener("pointermove",show);point.addEventListener("focus",()=>show({clientX:innerWidth/2,clientY:innerHeight/2}));
    point.addEventListener("pointerleave",()=>$("#tooltip").hidden=true);point.addEventListener("blur",()=>$("#tooltip").hidden=true);
  });
  renderScorecards(selectedPlayers, endpoint);
}

function renderScorecards(players, endpoint) {
  $("#scorecards").innerHTML = players.map(player => {
    const point = lastAtOrBefore(buildSeries(player,state), state.common ? endpoint : Infinity);
    const detail = state.metric === "trophyShare" ? `${point.tournamentsWon}/${point.tournaments} tournaments` : `${point.appearances} appearances · age ${point.age}`;
    return `<article class="scorecard" style="--player:${player.color}"><div class="value">${formatMetric(point.y,state.metric)}</div><h4>${player.shortName}</h4><p>${detail}</p></article>`;
  }).join("");
}

function renderCoverage(){ $("#coverage-body").innerHTML=data.players.map(p=>`<tr><td><strong>${p.name}</strong></td>${["goals","results","assists"].map(k=>`<td><span class="bar"><i style="width:${p.coverage[k]}%"></i></span>${p.coverage[k]}%</td>`).join("")}<td><span class="badge">${p.coverage.status}</span></td></tr>`).join(""); }
function render(){ renderPlayers(); renderChart(); renderCoverage(); }

[["#metric-select","metric"],["#axis-select","axis"],["#universe-select","universe"]].forEach(([selector,key])=>$(selector).addEventListener("change",e=>{state[key]=e.target.value;renderChart();}));
$("#common-support").addEventListener("change",e=>{state.common=e.target.checked;renderChart();});
render();

