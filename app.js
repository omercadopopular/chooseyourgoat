import { buildSeries, commonEndpoint, formatMetric, lastAtOrBefore, metricLabels, trimToCommon } from "./src/metrics.js";

const data = await fetch("./data/web_dataset.json").then(response => response.json());
const allBuckets = data.taxonomy.flatMap(group => group.children.map(child => child.id));
const state = {
  selected: new Set(["pele", "messi", "cristiano"]),
  buckets: new Set(allBuckets),
  metric: "goals",
  axis: "age",
  common: true
};
const $ = selector => document.querySelector(selector);
const playerGrid = $("#player-grid");

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
    renderPlayers();
    renderChart();
  }));
}

function setGroup(groupId, checked) {
  const group = data.taxonomy.find(item => item.id === groupId);
  group.children.forEach(child => checked ? state.buckets.add(child.id) : state.buckets.delete(child.id));
}

function updateRestrictionState() {
  for (const group of data.taxonomy) {
    const parent = document.querySelector(`[data-group="${group.id}"]`);
    const count = group.children.filter(child => state.buckets.has(child.id)).length;
    parent.checked = count === group.children.length;
    parent.indeterminate = count > 0 && count < group.children.length;
  }
  document.querySelectorAll("[data-bucket]").forEach(input => input.checked = state.buckets.has(input.dataset.bucket));
  const labels = data.taxonomy.flatMap(group => group.children).filter(child => state.buckets.has(child.id)).map(child => child.label);
  $("#restriction-summary").textContent = labels.length ? `${labels.length} categories included: ${labels.join(" · ")}` : "No categories selected. Choose at least one category to draw the chart.";
}

function renderRestrictions() {
  $("#restriction-groups").innerHTML = data.taxonomy.map(group => `
    <fieldset class="restriction-group">
      <label class="restriction-parent"><input type="checkbox" data-group="${group.id}">${group.label}</label>
      <div class="restriction-children">${group.children.map(child => `<label class="restriction-child"><input type="checkbox" data-bucket="${child.id}">${child.label}</label>`).join("")}</div>
    </fieldset>`).join("");
  document.querySelectorAll("[data-bucket]").forEach(input => input.addEventListener("change", () => {
    input.checked ? state.buckets.add(input.dataset.bucket) : state.buckets.delete(input.dataset.bucket);
    updateRestrictionState();
    renderChart();
  }));
  document.querySelectorAll("[data-group]").forEach(input => input.addEventListener("change", () => {
    setGroup(input.dataset.group, input.checked);
    updateRestrictionState();
    renderChart();
  }));
  document.querySelectorAll("[data-preset]").forEach(button => button.addEventListener("click", () => {
    state.buckets.clear();
    if (button.dataset.preset === "all") allBuckets.forEach(bucket => state.buckets.add(bucket));
    else setGroup(button.dataset.preset, true);
    updateRestrictionState();
    renderChart();
  }));
  updateRestrictionState();
}

function linePath(points, xScale, yScale) {
  return points.map((point, index) => `${index ? "L" : "M"}${xScale(point.x).toFixed(1)},${yScale(point.y).toFixed(1)}`).join(" ");
}

function renderChart() {
  const selectedPlayers = data.players.filter(player => state.selected.has(player.id));
  let entries = selectedPlayers.map(player => ({ player, points: buildSeries(player, { ...state, buckets: [...state.buckets] }) })).filter(entry => entry.points.length);
  if (!entries.length) {
    $("#chart").innerHTML = '<div class="empty-chart">No observations match these restrictions.</div>';
    $("#scorecards").innerHTML = "";
    $("#support-note").textContent = "Select at least one populated category";
    return;
  }
  const endpoint = commonEndpoint(entries.map(entry => entry.points));
  if (state.common) {
    const trimmed = trimToCommon(entries.map(entry => entry.points));
    entries = entries.map((entry, index) => ({ ...entry, points: trimmed[index] })).filter(entry => entry.points.length);
  }
  const all = entries.flatMap(entry => entry.points);
  const xMin = Math.min(...all.map(point => point.x));
  const xMax = Math.max(...all.map(point => point.x));
  const yMin = 0;
  const yMax = Math.max(...all.map(point => point.y)) * 1.08 || 1;
  const W = 1000, H = 420, pad = { l: 58, r: 25, t: 18, b: 42 };
  const x = value => pad.l + (value - xMin) / (xMax - xMin || 1) * (W - pad.l - pad.r);
  const y = value => H - pad.b - (value - yMin) / (yMax - yMin || 1) * (H - pad.t - pad.b);
  const ticks = Array.from({ length: 6 }, (_, index) => ({ value: yMin + (yMax - yMin) * index / 5, position: y(yMin + (yMax - yMin) * index / 5) }));
  const xTicks = Array.from({ length: 6 }, (_, index) => xMin + (xMax - xMin) * index / 5);
  const paths = entries.map(({ player, points }) => `<path class="series" stroke="${player.color}" d="${linePath(points, x, y)}"/>${points.map((point, index) => `<circle class="point" tabindex="0" data-player="${player.shortName}" data-x="${point.x}" data-y="${point.y}" data-year="${point.year}" data-apps="${point.appearances}" data-goals="${point.goals}" cx="${x(point.x)}" cy="${y(point.y)}" r="${index === points.length - 1 ? 5 : 3.5}" fill="${player.color}"/>`).join("")}`).join("");
  $("#chart").innerHTML = `<svg viewBox="0 0 ${W} ${H}" aria-hidden="true">${ticks.map(tick => `<line class="gridline" x1="${pad.l}" x2="${W - pad.r}" y1="${tick.position}" y2="${tick.position}"/><text class="axis-label" x="${pad.l - 10}" y="${tick.position + 3}" text-anchor="end">${formatMetric(tick.value, state.metric)}</text>`).join("")}${xTicks.map(value => `<text class="axis-label" x="${x(value)}" y="${H - 12}" text-anchor="middle">${state.axis === "age" ? value.toFixed(0) : Math.round(value)}</text>`).join("")}${paths}</svg>`;
  $("#chart-kicker").textContent = metricLabels[state.metric].toUpperCase();
  $("#chart-title").textContent = `By ${state.axis === "careerSeason" ? "career season" : state.axis}`;
  $("#legend").innerHTML = entries.map(({ player }) => `<span class="legend-item"><i class="dot" style="background:${player.color}"></i>${player.shortName}</span>`).join("");
  $("#support-note").textContent = state.common ? `Common endpoint: ${state.axis === "age" ? endpoint.toFixed(1) : Math.round(endpoint)} ${state.axis}` : `Full available careers · data cutoff ${data.meta.dataCutoff}`;
  $("#chart").querySelectorAll(".point").forEach(point => {
    const show = event => {
      const tip = $("#tooltip");
      tip.hidden = false;
      tip.innerHTML = `<strong>${point.dataset.player}</strong>Year ${point.dataset.year}<br>${metricLabels[state.metric]}: ${formatMetric(Number(point.dataset.y), state.metric)}<br>${Number(point.dataset.goals).toLocaleString()} goals / ${Number(point.dataset.apps).toLocaleString()} games`;
      tip.style.left = `${Math.min(innerWidth - 210, event.clientX + 12)}px`;
      tip.style.top = `${Math.max(8, event.clientY - 76)}px`;
    };
    point.addEventListener("pointerenter", show);
    point.addEventListener("pointermove", show);
    point.addEventListener("focus", () => show({ clientX: innerWidth / 2, clientY: innerHeight / 2 }));
    point.addEventListener("pointerleave", () => $("#tooltip").hidden = true);
    point.addEventListener("blur", () => $("#tooltip").hidden = true);
  });
  renderScorecards(entries, endpoint);
}

function renderScorecards(entries, endpoint) {
  $("#scorecards").innerHTML = entries.map(({ player }) => {
    const full = buildSeries(player, { ...state, buckets: [...state.buckets] });
    const point = lastAtOrBefore(full, state.common ? endpoint : Infinity);
    const detail = state.metric === "titles" ? `${point.titles} selected championship editions` : `${point.goals.toLocaleString()} goals / ${point.appearances.toLocaleString()} games`;
    return `<article class="scorecard" style="--player:${player.color}"><div class="value">${formatMetric(point.y, state.metric)}</div><h4>${player.shortName}</h4><p>${detail}</p></article>`;
  }).join("");
}

function renderCoverage() {
  $("#coverage-body").innerHTML = data.players.map(player => `<tr><td><strong>${player.name}</strong></td><td>${player.coverage.club}</td><td>${player.coverage.national}</td><td>${player.coverage.titles}</td><td><span class="badge">Sourced</span></td></tr>`).join("");
}

[["#metric-select", "metric"], ["#axis-select", "axis"]].forEach(([selector, key]) => $(selector).addEventListener("change", event => {
  state[key] = event.target.value;
  renderChart();
}));
$("#common-support").addEventListener("change", event => {
  state.common = event.target.checked;
  renderChart();
});

renderPlayers();
renderRestrictions();
renderCoverage();
renderChart();
