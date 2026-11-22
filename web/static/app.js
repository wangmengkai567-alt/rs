
const element = id => document.getElementById(id);
const formatCount = new Intl.NumberFormat("zh-CN");
const map = L.map("map").setView([30.2672, -97.7431], 11);

L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).on("tileerror", () => {
  if (!element("map-tile-warning")) {
    const status = document.createElement("p");
    status.id = "map-tile-warning";
    status.className = "hint";
    status.textContent = "部分底图瓦片暂时无法加载。";
    element("map").after(status);
  }
}).addTo(map);
const overlays = L.layerGroup().addTo(map);
const queryPoints = L.layerGroup().addTo(map);

const form = element("query-form");
const submit = element("submit");
const loadMore = element("load-more");
const selectionStatus = element("selection-status");
let selection = null;
let activeQuery = null;
let queryItems = [];
let cursor = null;
let busy = false;
let ready = false;

async function fetchJson(url) {
  const response = await fetch(url, {cache: "no-store"});
  const data = await response.json();
  if (!response.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : "查询参数有误或数据尚未就绪。");
  }
  return data;
}

function setStatus(message, error = false) {
  const status = element("result-status");
  status.textContent = message;
  status.dataset.error = error;
}

function mode() {
  return new FormData(form).get("mode");
}

function endSelection(message = "") {
  selection = null;
  element("map").classList.remove("selecting");
  selectionStatus.textContent = message;
  element("select-region").textContent = "地图上选范围";
}

function applyMode() {
  const region = mode() === "region";
  element("user-fields").hidden = region;
  element("region-fields").hidden = !region;
  element("user-id").disabled = region;
  element("bbox").disabled = !region;
  endSelection();
  overlays.clearLayers();
}

form.querySelectorAll('[name="mode"]').forEach(input => input.addEventListener("change", applyMode));

element("select-region").addEventListener("click", () => {
  if (selection !== null) {
    endSelection();
    overlays.clearLayers();
    return;
  }
  overlays.clearLayers();
  selection = {};
  element("map").classList.add("selecting");
  element("select-region").textContent = "取消选取";
  selectionStatus.textContent = "请单击范围的第一个角。";
});

element("clear-region").addEventListener("click", () => {
  element("bbox").value = "";
  overlays.clearLayers();
  endSelection();
});

map.on("click", event => {
  if (selection === null) return;
  if (!selection.first) {
    selection.first = event.latlng.wrap();
    L.circleMarker(selection.first, {radius: 5, color: "#1b5c4c"}).addTo(overlays);
    selectionStatus.textContent = "请单击范围的对角。";
    return;
  }
  const corner = event.latlng.wrap();
  const bounds = L.latLngBounds(selection.first, corner);
  const coordinates = [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()];
  element("bbox").value = coordinates.map(value => value.toFixed(5)).join(",");
  overlays.clearLayers();
  L.rectangle(bounds, {color: "#20806e", weight: 2, fillOpacity: .1}).addTo(overlays);
  endSelection("范围已选定，点击查询查看签到。");
});

function updateTable(items, reset) {
  const rows = element("rows");
  if (reset) rows.replaceChildren();
  const fragment = document.createDocumentFragment();
  for (const item of items) {
    const [lon, lat] = item.coordinates;
    const row = document.createElement("tr");
    for (const value of [item.source_line, item.ts_utc, item.user_id, item.location_id,
      lon.toFixed(6), lat.toFixed(6)]) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    }
    fragment.append(row);
  }
  rows.append(fragment);
}

function renderPoints(query, fit) {
  queryPoints.clearLayers();
  const points = [];
  for (const item of queryItems) {
    const [lon, lat] = item.coordinates;
    const point = [lat, lon];
    points.push(point);
    const popup = document.createElement("div");
    for (const line of [
      "用户 " + item.user_id + " · 地点 " + item.location_id,
      "所属分片 " + item.shard,
      item.ts_utc,
      lon.toFixed(6) + ", " + lat.toFixed(6),
    ]) {
      const row = document.createElement("div");
      row.textContent = line;
      popup.append(row);
    }
    L.circleMarker(point, {className: "checkin-point " + item.shard, radius: 5, color: "#fff",
      fillOpacity: .95, weight: 1}).bindPopup(popup).addTo(queryPoints);
  }
  if (query.mode === "trajectory" && points.length > 1) {
    L.polyline([...points].reverse(), {color: "#207d6a", weight: 2}).addTo(queryPoints).bringToBack();
  }
  if (!fit) return;

  if (query.mode === "region") {
    const [west, south, east, north] = query.params.get("bbox").split(",").map(Number);
    const bounds = L.latLngBounds([south, west], [north, east]);
    overlays.clearLayers();
    L.rectangle(bounds, {color: "#20806e", weight: 2, fillOpacity: .1}).addTo(overlays);
    map.fitBounds(bounds, {padding: [20, 20], maxZoom: 15});
  } else if (points.length) {
    map.fitBounds(L.latLngBounds(points), {padding: [24, 24], maxZoom: 15});
  }
}

async function runQuery(query, next) {
  if (busy) return;
  busy = true;
  submit.disabled = true;
  loadMore.disabled = true;
  setStatus("正在查询…");
  try {
    const params = new URLSearchParams(query.params);
    if (next) params.set("cursor", cursor);
    const result = await fetchJson(query.path + "?" + params);
    if (!next) {
      queryItems = [];
      if (query.mode === "trajectory") overlays.clearLayers();
    }
    activeQuery = query;
    cursor = result.next_cursor;
    queryItems.push(...result.items);
    updateTable(result.items, !next);
    renderPoints(query, !next);
    const countText = "已加载 " + formatCount.format(queryItems.length) + " 条签到。";
    setStatus(queryItems.length ? countText : "该条件下没有签到记录。");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    busy = false;
    submit.disabled = false;
    loadMore.disabled = false;
    loadMore.hidden = !cursor;
  }
}

form.addEventListener("submit", event => {
  event.preventDefault();
  const input = new FormData(form);
  const queryMode = input.get("mode");
  const params = new URLSearchParams();
  for (const field of ["start", "end"]) {
    const value = input.get(field).trim();
    if (value) params.set(field, value);
  }
  let path;
  if (queryMode === "region") {
    const bbox = input.get("bbox").trim();
    if (!bbox) {
      setStatus("请填写经纬度范围或在地图上选择。", true);
      return;
    }
    params.set("bbox", bbox);
    path = "/api/checkins/geo";
  } else {
    path = "/api/users/" + encodeURIComponent(input.get("user").trim()) + "/trajectory";
  }
  endSelection();
  runQuery({mode: queryMode, path, params}, false);
});

loadMore.addEventListener("click", () => {
  if (activeQuery && cursor) runQuery(activeQuery, true);
});

async function loadOverview() {
  const status = element("service-status");
  try {
    const health = await fetch("/api/health", {cache: "no-store"});
    const state = await health.json();
    if (!health.ok) {
      const messages = {
        unavailable: "数据库未连接",
        not_loaded: "等待导入",
        loading: "正在导入与验收",
        failed: "导入失败",
      };
      status.textContent = messages[state.dataset] || "数据尚未就绪";
      return;
    }
    const data = await fetchJson("/api/stats/overview");
    for (const [id, key] of Object.entries({
      "checkin-count": "clean_count",
      "user-count": "user_count",
      "location-count": "location_count",
      "reject-count": "reject_count",
    })) {
      element(id).textContent = formatCount.format(data[key]);
    }
    element("dataset-range").textContent = data.first_ts_utc + " 至 " + data.last_ts_utc +
      " · 输入 " + formatCount.format(data.input_count) + " 条";
    Object.keys(data.shard_counts).sort().forEach((name, index) => {
      const count = data.shard_counts[name];
      element("shard-counts").children[index].querySelector("dd").textContent = formatCount.format(count);
      element("shard-meter").children[index].style.width = (100 * count / data.clean_count) + "%";
    });
    status.textContent = "数据已就绪";
    ready = true;
  } catch {
    status.textContent = "服务暂不可用";
  } finally {
    if (!ready) window.setTimeout(loadOverview, 6000);
  }
}
loadOverview();
