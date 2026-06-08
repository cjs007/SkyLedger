const statusList = document.querySelector("#statusList");
const configList = document.querySelector("#configList");
const testResult = document.querySelector("#testResult");
const settingsResult = document.querySelector("#settingsResult");
const mapZoomRange = document.querySelector("#mapZoomRange");
const mapZoomNumber = document.querySelector("#mapZoomNumber");
const homeNameInput = document.querySelector("#homeNameInput");
const homeLatInput = document.querySelector("#homeLatInput");
const homeLonInput = document.querySelector("#homeLonInput");
const homeSettingsResult = document.querySelector("#homeSettingsResult");
const lowMarkerColorInput = document.querySelector("#lowMarkerColorInput");
const defaultMarkerColorInput = document.querySelector("#defaultMarkerColorInput");
const markerColorsResult = document.querySelector("#markerColorsResult");
let homeFormDirty = false;
let markerColorsDirty = false;

function rows(data) {
  return Object.entries(data).map(([key, value]) => `
    <dt>${escapeHtml(key.replaceAll("_", " "))}</dt>
    <dd>${escapeHtml(displayValue(value))}</dd>
  `).join("");
}

function displayValue(value) {
  return value === null || value === undefined || value === "" ? "--" : String(value);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
  }[char]));
}

async function loadStatus() {
  const response = await fetch("/api/status");
  const status = await response.json();
  const config = status.config || {};
  setMapZoom(config.map_zoom_level ?? 13);
  if (!homeFormDirty) setHomeFields(config);
  if (!markerColorsDirty) setMarkerColorFields(config);
  statusList.innerHTML = rows({
    receiver_online: status.receiver_online,
    source: status.source,
    raw_aircraft_count: status.raw_aircraft_count,
    normalized_aircraft_count: status.normalized_aircraft_count,
    last_success_at: status.last_success_at,
    last_error: status.last_error,
    database_path: status.database_path,
  });
  configList.innerHTML = rows(config);
}

function setHomeFields(config) {
  homeNameInput.value = config.home_name ?? "";
  homeLatInput.value = config.home_lat ?? "";
  homeLonInput.value = config.home_lon ?? "";
}

function readCoordinate(input) {
  const text = input.value.trim();
  if (!text) return null;
  const value = Number(text);
  return Number.isFinite(value) ? value : null;
}

function setMarkerColorFields(config) {
  lowMarkerColorInput.value = readHexColor(config.aircraft_marker_low_color, "#61f4a8");
  defaultMarkerColorInput.value = readHexColor(config.aircraft_marker_default_color, "#6ee7ff");
}

function readHexColor(value, fallback = null) {
  const color = String(value || "").trim().toLowerCase();
  if (/^#[0-9a-f]{6}$/.test(color)) return color;
  return fallback;
}

function setMapZoom(value) {
  const zoom = Math.max(0, Math.min(19, Number.parseInt(value, 10) || 0));
  mapZoomRange.value = zoom;
  mapZoomNumber.value = zoom;
}

async function post(path) {
  testResult.textContent = "Running...";
  try {
    const response = await fetch(path, { method: "POST" });
    const payload = await response.json();
    if (payload.deleted) {
      const total = Object.values(payload.deleted).reduce((sum, count) => sum + Number(count || 0), 0);
      testResult.textContent = `Cleared ${total} history row(s)`;
      await loadStatus();
      return;
    }
    testResult.textContent = payload.error || (payload.ok === false ? "Test accepted" : "Test sent");
  } catch (error) {
    testResult.textContent = "Test failed";
  }
}

async function readJson(response) {
  try {
    return await response.json();
  } catch {
    return {};
  }
}

function saveFailureText(label, error) {
  const message = error?.message && error.message !== "Save failed" ? `: ${error.message}` : "";
  return `${label}${message}`;
}

document.querySelector("#testCountdown").addEventListener("click", () => post("/api/test-countdown"));
document.querySelector("#testDiscord").addEventListener("click", () => post("/api/test-discord"));
document.querySelector("#clearHistory").addEventListener("click", () => {
  const confirmed = window.confirm("Clear all logged aircraft, flyover events, daily stats, and raw positions?");
  if (confirmed) post("/api/history/clear");
});
mapZoomRange.addEventListener("input", () => setMapZoom(mapZoomRange.value));
mapZoomNumber.addEventListener("input", () => setMapZoom(mapZoomNumber.value));
for (const input of [homeNameInput, homeLatInput, homeLonInput]) {
  input.addEventListener("input", () => {
    homeFormDirty = true;
  });
}
for (const input of [lowMarkerColorInput, defaultMarkerColorInput]) {
  input.addEventListener("input", () => {
    markerColorsDirty = true;
  });
}
document.querySelector("#saveHomeSettings").addEventListener("click", async () => {
  homeSettingsResult.textContent = "Saving...";
  const homeName = homeNameInput.value.trim();
  const homeLat = readCoordinate(homeLatInput);
  const homeLon = readCoordinate(homeLonInput);
  if (!homeName || homeLat === null || homeLon === null) {
    homeSettingsResult.textContent = "Home save failed";
    return;
  }
  try {
    const response = await fetch("/api/settings/home", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        home_name: homeName,
        home_lat: homeLat,
        home_lon: homeLon,
      }),
    });
    const payload = await readJson(response);
    if (!response.ok || payload.ok === false) throw new Error(payload.detail || "Save failed");
    setHomeFields(payload);
    homeFormDirty = false;
    homeSettingsResult.textContent = "Home saved";
    await loadStatus();
  } catch (error) {
    homeSettingsResult.textContent = saveFailureText("Home save failed", error);
  }
});
document.querySelector("#saveMarkerColors").addEventListener("click", async () => {
  markerColorsResult.textContent = "Saving...";
  const lowColor = readHexColor(lowMarkerColorInput.value);
  const defaultColor = readHexColor(defaultMarkerColorInput.value);
  if (!lowColor || !defaultColor) {
    markerColorsResult.textContent = "Marker color save failed";
    return;
  }
  try {
    const response = await fetch("/api/settings/aircraft-marker-colors", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        aircraft_marker_low_color: lowColor,
        aircraft_marker_default_color: defaultColor,
      }),
    });
    const payload = await readJson(response);
    if (!response.ok || payload.ok === false) throw new Error(payload.detail || "Save failed");
    setMarkerColorFields(payload);
    markerColorsDirty = false;
    markerColorsResult.textContent = "Marker colors saved";
    await loadStatus();
  } catch (error) {
    markerColorsResult.textContent = saveFailureText("Marker color save failed", error);
  }
});
document.querySelector("#saveMapZoom").addEventListener("click", async () => {
  settingsResult.textContent = "Saving...";
  try {
    const response = await fetch("/api/settings/map-zoom", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ map_zoom_level: Number(mapZoomNumber.value) }),
    });
    const payload = await readJson(response);
    if (!response.ok || payload.ok === false) throw new Error(payload.detail || "Save failed");
    setMapZoom(payload.map_zoom_level);
    settingsResult.textContent = `Map zoom saved at ${payload.map_zoom_level}`;
    await loadStatus();
  } catch (error) {
    settingsResult.textContent = saveFailureText("Map zoom save failed", error);
  }
});
loadStatus();
setInterval(loadStatus, 5000);
