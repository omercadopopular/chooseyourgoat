import { buildCompetitionSeries, buildSeries, commonEndpoint, formatMetric, lastAtOrBefore, trimToCommon } from "./src/metrics.js";
import { getInitialLanguage, localeFor, saveLanguage, supportedLanguages, taxonomyLabel, translate, translateCountry } from "./src/i18n.js";

const data = await fetch("./data/web_dataset.json").then(response => response.json());
const allBuckets = data.taxonomy.flatMap(group => group.children.map(child => child.id));
const competitionTaxonomy = data.taxonomy.map(group => ({
  ...group,
  children: group.children.filter(child => child.id !== "national_team_friendlies")
}));
const competitionBuckets = competitionTaxonomy.flatMap(group => group.children.map(child => child.id));
const state = {
  selected: new Set(["pele", "messi", "cristiano"]),
  buckets: new Set(allBuckets),
  metric: "goals",
  axis: "age",
  common: true
};
const competitionState={metric:"competitionsWon",axis:"competitionCount",common:true,buckets:new Set(competitionBuckets)};
const playerFilter={query:"",era:"all",role:"all",country:"all"};
const $ = selector => document.querySelector(selector);
const playerGrid = $("#player-grid");
let language = getInitialLanguage();
const t = (key, values) => translate(language, key, values);
const metricKey = { goals: "cumulativeGoals", goalsPerGame: "cumulativeGoalsPerGame", marginalGoalsPerGame: "marginalGoalsPerGame", competitionsWon: "cumulativeCompetitionsWon", cumulativeCompetitionWinRate: "cumulativeWinRate" };
const axisKey = { age: "age", appearances: "appearances", careerSeason: "careerSeason", competitionCount: "competitionsPlayed" };
const localizedMetric = metric => t(metricKey[metric]);
const localizedAxis = axis => t(axisKey[axis]);
const formatValue = (value, metric) => formatMetric(value, metric, localeFor(language));

function applyStaticTranslations() {
  document.documentElement.lang = language === "pt" ? "pt-BR" : language;
  document.title = t("pageTitle");
  document.querySelector('meta[name="description"]').content = t("metaDescription");
  document.querySelectorAll("[data-i18n]").forEach(node => node.textContent = t(node.dataset.i18n));
  document.querySelectorAll("[data-i18n-html]").forEach(node => node.innerHTML = t(node.dataset.i18nHtml));
  document.querySelectorAll("[data-i18n-placeholder]").forEach(node => node.placeholder = t(node.dataset.i18nPlaceholder));
  document.querySelectorAll("[data-i18n-aria]").forEach(node => node.setAttribute("aria-label", t(node.dataset.i18nAria)));
  document.querySelectorAll("[data-language]").forEach(button => {
    const active = button.dataset.language === language;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
}

function renderCountryOptions() {
  const select = $("#country-filter");
  const current = select.value || playerFilter.country;
  const countries = [...new Set(data.players.map(player => player.country))].sort((a, b) => translateCountry(language, a).localeCompare(translateCountry(language, b), localeFor(language)));
  select.innerHTML = `<option value="all">${t("allCountries")}</option>` + countries.map(country => `<option value="${country}">${translateCountry(language, country)}</option>`).join("");
  select.value = current;
}

function renderPlayers() {
  const visible=data.players.filter(player=>{
    const haystack=`${player.name} ${player.shortName} ${player.country}`.toLowerCase();
    return (!playerFilter.query||haystack.includes(playerFilter.query))&&(playerFilter.era==="all"||player.era===playerFilter.era)&&(playerFilter.role==="all"||player.role===playerFilter.role)&&(playerFilter.country==="all"||player.country===playerFilter.country);
  });
  playerGrid.innerHTML = visible.length?visible.map((player) => `
    <button class="player-card ${state.selected.has(player.id) ? "selected" : ""}" data-id="${player.id}" aria-pressed="${state.selected.has(player.id)}">
      <span class="number">${player.eraLabel||player.years.split('–')[0]}</span><span class="check">${state.selected.has(player.id) ? "●" : "○"}</span>
      <strong>${player.shortName}</strong><small>${translateCountry(language, player.country)} · ${player.years}</small>
    </button>`).join(""):`<div class="player-empty">${t("noPlayers")}</div>`;
  $("#selected-tray").innerHTML=`<strong>${state.selected.size} ${t("selected")}</strong>`+data.players.filter(p=>state.selected.has(p.id)).map(p=>`<span class="selected-chip">${p.shortName}</span>`).join('')+`<span class="selection-actions"><button type="button" data-select-all>${t("selectAll",{count:data.players.length})}</button><button type="button" data-reset-selection>${t("reset")}</button></span>`;
  playerGrid.querySelectorAll("button").forEach(button => button.addEventListener("click", () => {
    const id = button.dataset.id;
    if (state.selected.has(id) && state.selected.size > 2) state.selected.delete(id);
    else if (!state.selected.has(id)) state.selected.add(id);
    renderPlayers();
    renderChart();
    renderCompetitionChart();
  }));
  $("[data-select-all]").addEventListener("click",()=>{
    state.selected=new Set(data.players.map(player=>player.id));
    renderPlayers(); renderChart(); renderCompetitionChart();
  });
  $("[data-reset-selection]").addEventListener("click",()=>{
    state.selected=new Set(["pele","messi","cristiano"]);
    renderPlayers(); renderChart(); renderCompetitionChart();
  });
}

function setupPlayerFilters(){
  renderCountryOptions();
  $("#player-search").addEventListener('input',e=>{playerFilter.query=e.target.value.trim().toLowerCase();renderPlayers();});
  [["#era-filter","era"],["#role-filter","role"],["#country-filter","country"]].forEach(([selector,key])=>$(selector).addEventListener('change',e=>{playerFilter[key]=e.target.value;renderPlayers();}));
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
  const labels = data.taxonomy.flatMap(group => group.children).filter(child => state.buckets.has(child.id)).map(child => taxonomyLabel(language, child.id));
  $("#restriction-summary").textContent = labels.length ? t("categoriesIncluded", {count: labels.length, labels: labels.join(" · ")}) : t("noCategories");
}

function renderRestrictions() {
  $("#restriction-groups").innerHTML = data.taxonomy.map(group => `
    <fieldset class="restriction-group">
      <label class="restriction-parent"><input type="checkbox" data-group="${group.id}">${taxonomyLabel(language, group.id)}</label>
      <div class="restriction-children">${group.children.map(child => `<label class="restriction-child"><input type="checkbox" data-bucket="${child.id}">${taxonomyLabel(language, child.id)}</label>`).join("")}</div>
    </fieldset>`).join("");
  document.querySelectorAll("[data-bucket]").forEach(input => input.onchange = () => {
    input.checked ? state.buckets.add(input.dataset.bucket) : state.buckets.delete(input.dataset.bucket);
    updateRestrictionState();
    renderChart();
  });
  document.querySelectorAll("[data-group]").forEach(input => input.onchange = () => {
    setGroup(input.dataset.group, input.checked);
    updateRestrictionState();
    renderChart();
  });
  document.querySelectorAll("[data-preset]").forEach(button => button.onclick = () => {
    state.buckets.clear();
    if (button.dataset.preset === "all") allBuckets.forEach(bucket => state.buckets.add(bucket));
    else setGroup(button.dataset.preset, true);
    updateRestrictionState();
    renderChart();
  });
  updateRestrictionState();
}

function renderCompetitionRestrictions(){
  $("#competition-restriction-groups").innerHTML=competitionTaxonomy.map(group=>`
    <fieldset class="restriction-group">
      <label class="restriction-parent"><input type="checkbox" data-competition-group="${group.id}">${taxonomyLabel(language, group.id, true)}</label>
      <div class="restriction-children">${group.children.map(child=>`<label class="restriction-child"><input type="checkbox" data-competition-bucket="${child.id}">${taxonomyLabel(language, child.id, true)}</label>`).join('')}</div>
    </fieldset>`).join('');
  const update=()=>{
    for(const group of competitionTaxonomy){const parent=document.querySelector(`[data-competition-group="${group.id}"]`);const count=group.children.filter(c=>competitionState.buckets.has(c.id)).length;parent.checked=count===group.children.length;parent.indeterminate=count>0&&count<group.children.length;}
    document.querySelectorAll('[data-competition-bucket]').forEach(i=>i.checked=competitionState.buckets.has(i.dataset.competitionBucket));
    const labels=competitionTaxonomy.flatMap(g=>g.children).filter(c=>competitionState.buckets.has(c.id)).map(c=>taxonomyLabel(language,c.id,true));$("#competition-restriction-summary").textContent=labels.length?t("competitionCategoriesIncluded",{count:labels.length,labels:labels.join(' · ')}):t("noCompetitionCategories");
  };
  document.querySelectorAll('[data-competition-bucket]').forEach(input=>input.onchange=()=>{input.checked?competitionState.buckets.add(input.dataset.competitionBucket):competitionState.buckets.delete(input.dataset.competitionBucket);update();renderCompetitionChart();});
  document.querySelectorAll('[data-competition-group]').forEach(input=>input.onchange=()=>{const group=competitionTaxonomy.find(g=>g.id===input.dataset.competitionGroup);group.children.forEach(c=>input.checked?competitionState.buckets.add(c.id):competitionState.buckets.delete(c.id));update();renderCompetitionChart();});
  document.querySelectorAll('[data-competition-preset]').forEach(button=>button.onclick=()=>{competitionState.buckets.clear();if(button.dataset.competitionPreset==='all')competitionBuckets.forEach(b=>competitionState.buckets.add(b));else competitionTaxonomy.find(g=>g.id===button.dataset.competitionPreset).children.forEach(c=>competitionState.buckets.add(c.id));update();renderCompetitionChart();});
  update();
}

function linePath(points, xScale, yScale) {
  return points.map((point, index) => `${index ? "L" : "M"}${xScale(point.x).toFixed(1)},${yScale(point.y).toFixed(1)}`).join(" ");
}

function renderChart() {
  const selectedPlayers = data.players.filter(player => state.selected.has(player.id));
  let entries = selectedPlayers.map(player => ({ player, points: buildSeries(player, { ...state, buckets: [...state.buckets] }) })).filter(entry => entry.points.length);
  if (!entries.length) {
    $("#chart").innerHTML = `<div class="empty-chart">${t("noObservations")}</div>`;
    $("#scorecards").innerHTML = "";
    $("#support-note").textContent = t("selectPopulated");
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
  $("#chart").innerHTML = `<svg viewBox="0 0 ${W} ${H}" aria-hidden="true">${ticks.map(tick => `<line class="gridline" x1="${pad.l}" x2="${W - pad.r}" y1="${tick.position}" y2="${tick.position}"/><text class="axis-label" x="${pad.l - 10}" y="${tick.position + 3}" text-anchor="end">${formatValue(tick.value, state.metric)}</text>`).join("")}${xTicks.map(value => `<text class="axis-label" x="${x(value)}" y="${H - 12}" text-anchor="middle">${state.axis === "age" ? value.toFixed(0) : Math.round(value).toLocaleString(localeFor(language))}</text>`).join("")}${paths}</svg>`;
  $("#chart-kicker").textContent = localizedMetric(state.metric).toLocaleUpperCase(localeFor(language));
  $("#chart-title").textContent = t("byAxis", {axis: localizedAxis(state.axis).toLocaleLowerCase(localeFor(language))});
  $("#legend").innerHTML = entries.map(({ player }) => `<span class="legend-item"><i class="dot" style="background:${player.color}"></i>${player.shortName}</span>`).join("");
  $("#support-note").textContent = state.common ? t("commonEndpoint", {value: state.axis === "age" ? endpoint.toFixed(1) : Math.round(endpoint).toLocaleString(localeFor(language)), axis: localizedAxis(state.axis).toLocaleLowerCase(localeFor(language))}) : t("fullCareers", {cutoff:data.meta.dataCutoff});
  $("#chart").querySelectorAll(".point").forEach(point => {
    const show = event => {
      const tip = $("#tooltip");
      tip.hidden = false;
      tip.innerHTML = `<strong>${point.dataset.player}</strong>${t("year")} ${point.dataset.year}<br>${localizedMetric(state.metric)}: ${formatValue(Number(point.dataset.y), state.metric)}<br>${Number(point.dataset.goals).toLocaleString(localeFor(language))} ${t("goals")} / ${Number(point.dataset.apps).toLocaleString(localeFor(language))} ${t("games")}`;
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
    const detail = state.metric === "titles" ? `${point.titles.toLocaleString(localeFor(language))} ${t("selectedEditions")}` : `${point.goals.toLocaleString(localeFor(language))} ${t("goals")} / ${point.appearances.toLocaleString(localeFor(language))} ${t("games")}`;
    return `<article class="scorecard" style="--player:${player.color}"><div class="value">${formatValue(point.y, state.metric)}</div><h4>${player.shortName}</h4><p>${detail}</p></article>`;
  }).join("");
}

function renderCompetitionChart(){
  let entries=data.players.filter(p=>state.selected.has(p.id)).map(player=>({player,points:buildCompetitionSeries(player,{...competitionState,buckets:[...competitionState.buckets]})})).filter(e=>e.points.length);
  const target=$("#competition-chart");
  if(!entries.length){target.innerHTML=`<div class="empty-chart">${t("noEditions")}</div>`;$("#competition-scorecards").innerHTML="";return;}
  const endpoint=commonEndpoint(entries.map(e=>e.points));
  if(competitionState.common){const trimmed=trimToCommon(entries.map(e=>e.points));entries=entries.map((e,i)=>({...e,points:trimmed[i]})).filter(e=>e.points.length);}
  const all=entries.flatMap(e=>e.points),xMin=Math.min(...all.map(p=>p.x)),xMax=Math.max(...all.map(p=>p.x)),yMax=Math.max(...all.map(p=>p.y))*1.08||1;
  const W=1000,H=420,pad={l:58,r:25,t:18,b:42},x=v=>pad.l+(v-xMin)/(xMax-xMin||1)*(W-pad.l-pad.r),y=v=>H-pad.b-v/(yMax||1)*(H-pad.t-pad.b);
  const ticks=Array.from({length:6},(_,i)=>yMax*i/5),xTicks=Array.from({length:6},(_,i)=>xMin+(xMax-xMin)*i/5);
  const paths=entries.map(({player,points})=>`<path class="series" stroke="${player.color}" d="${linePath(points,x,y)}"/>${points.map((p,i)=>`<circle class="point competition-point" tabindex="0" data-player="${player.shortName}" data-year="${p.year}" data-y="${p.y}" data-played="${p.played}" data-won="${p.won}" data-period-played="${p.periodPlayed}" data-period-won="${p.periodWon}" cx="${x(p.x)}" cy="${y(p.y)}" r="${i===points.length-1?5:3.5}" fill="${player.color}"/>`).join("")}`).join("");
  target.innerHTML=`<svg viewBox="0 0 ${W} ${H}">${ticks.map(v=>`<line class="gridline" x1="${pad.l}" x2="${W-pad.r}" y1="${y(v)}" y2="${y(v)}"/><text class="axis-label" x="${pad.l-10}" y="${y(v)+3}" text-anchor="end">${formatValue(v,competitionState.metric)}</text>`).join("")}${xTicks.map(v=>`<text class="axis-label" x="${x(v)}" y="${H-12}" text-anchor="middle">${competitionState.axis==="age"?v.toFixed(0):Math.round(v).toLocaleString(localeFor(language))}</text>`).join("")}${paths}</svg>`;
  $("#competition-chart-kicker").textContent=localizedMetric(competitionState.metric).toLocaleUpperCase(localeFor(language));
  $("#competition-chart-title").textContent=t("byAxis",{axis:localizedAxis(competitionState.axis).toLocaleLowerCase(localeFor(language))});
  $("#competition-legend").innerHTML=entries.map(({player})=>`<span class="legend-item"><i class="dot" style="background:${player.color}"></i>${player.shortName}</span>`).join("");
  $("#competition-support-note").textContent=competitionState.common?t("commonEndpoint",{value:competitionState.axis==="age"?endpoint.toFixed(1):Math.round(endpoint).toLocaleString(localeFor(language)),axis:localizedAxis(competitionState.axis).toLocaleLowerCase(localeFor(language))}):t("fullEditions",{cutoff:data.meta.dataCutoff});
  target.querySelectorAll('.competition-point').forEach(point=>{const show=e=>{const tip=$("#tooltip");tip.hidden=false;tip.innerHTML=`<strong>${point.dataset.player}</strong>${t("year")} ${point.dataset.year}<br>${localizedMetric(competitionState.metric)}: ${formatValue(Number(point.dataset.y),competitionState.metric)}<br>${point.dataset.won} ${t("won")} / ${point.dataset.played} ${t("played")} ${t("cumulative")}<br>${point.dataset.periodWon} / ${point.dataset.periodPlayed} ${t("inPeriod")}`;tip.style.left=`${Math.min(innerWidth-230,e.clientX+12)}px`;tip.style.top=`${Math.max(8,e.clientY-90)}px`;};point.addEventListener('pointerenter',show);point.addEventListener('pointermove',show);point.addEventListener('pointerleave',()=>$("#tooltip").hidden=true);});
  $("#competition-scorecards").innerHTML=entries.map(({player,points})=>{const p=points.at(-1),c=player.competitionCoverage,excluded=c.excludedHonours?.length||0,unnamed=c.excludedAggregateRows?.length||0,coverage=c.reconciliationStatus==="partial"?t("reconciliationPartial"):excluded?t("honoursAdjudicated",{count:excluded}):unnamed?t("honoursMatchedUnnamed",{count:unnamed}):t("honoursMatched");return `<article class="scorecard" style="--player:${player.color}"><div class="value">${formatValue(p.y,competitionState.metric)}</div><h4>${player.shortName}</h4><p>${p.won.toLocaleString(localeFor(language))} ${t("won")} / ${p.played.toLocaleString(localeFor(language))} ${t("played")} · ${coverage}</p></article>`;}).join("");
}

function renderCoverage() {
  $("#coverage-body").innerHTML = data.players.map(player => `<tr><td><strong>${player.name}</strong></td><td>${translateCoverage(player.coverage.club)}</td><td>${translateCoverage(player.coverage.national)}</td><td>${translateCoverage(player.coverage.titles)}</td><td><span class="badge">${t("sourced")}</span></td></tr>`).join("");
}

function translateCoverage(value) {
  if (language === "en") return value;
  if (value === "Career-spanning season/competition aggregates") return language === "es" ? "Agregados de temporada/competición de toda la carrera" : "Agregados de temporada/competição de toda a carreira";
  let match = value.match(/^(\d+) complete senior caps$/);
  if (match) return language === "es" ? `${match[1]} partidos completos con la selección absoluta` : `${match[1]} jogos completos pela seleção principal`;
  match = value.match(/^(\d+) senior caps allocated by competition family$/);
  if (match) return language === "es" ? `${match[1]} partidos de selección asignados por familia de competición` : `${match[1]} jogos pela seleção alocados por família de competição`;
  match = value.match(/^(\d+) counted championship editions; all reported honours adjudicated$/);
  if (match) return language === "es" ? `${match[1]} ediciones de campeonato contabilizadas; todos los honores revisados` : `${match[1]} edições de campeonato contabilizadas; todas as honrarias revisadas`;
  return value;
}

[["#metric-select", "metric"], ["#axis-select", "axis"]].forEach(([selector, key]) => $(selector).addEventListener("change", event => {
  state[key] = event.target.value;
  renderChart();
}));
$("#common-support").addEventListener("change", event => {
  state.common = event.target.checked;
  renderChart();
});
[["#competition-metric-select","metric"],["#competition-axis-select","axis"]].forEach(([selector,key])=>$(selector).addEventListener("change",event=>{competitionState[key]=event.target.value;renderCompetitionChart();}));
$("#competition-common-support").addEventListener("change",event=>{competitionState.common=event.target.checked;renderCompetitionChart();});

function setLanguage(nextLanguage) {
  if (!supportedLanguages.includes(nextLanguage)) return;
  language = nextLanguage;
  saveLanguage(language);
  applyStaticTranslations();
  renderCountryOptions();
  renderPlayers();
  renderRestrictions();
  renderCompetitionRestrictions();
  renderCoverage();
  renderChart();
  renderCompetitionChart();
}

document.querySelectorAll("[data-language]").forEach(button => button.addEventListener("click", () => setLanguage(button.dataset.language)));
applyStaticTranslations();
renderPlayers();
setupPlayerFilters();
renderRestrictions();
renderCompetitionRestrictions();
renderCoverage();
renderChart();
renderCompetitionChart();
