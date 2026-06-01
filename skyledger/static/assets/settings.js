const statusList = document.querySelector("#statusList");
const configList = document.querySelector("#configList");
const testResult = document.querySelector("#testResult");
const settingsResult = document.querySelector("#settingsResult");
const mapZoomRange = document.querySelector("#mapZoomRange");
const mapZoomNumber = document.querySelector("#mapZoomNumber");

function rows(data) {
  return Object.entries(data).map(([key, value]) => `
    <dt>${key.replaceAll("_", " ")}</dt>
    <dd>${value === null || value === undefined || value === "" ? "--" : value}</dd>
  `).join("");
}

async function loadStatus() {
  const response = await fetch("/api/status");
  const status = await response.json();
  const config = status.config || {};
  setMapZoom(config.map_zoom_level ?? 13);
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

document.querySelector("#testCountdown").addEventListener("click", () => post("/api/test-countdown"));
document.querySelector("#testDiscord").addEventListener("click", () => post("/api/test-discord"));
document.querySelector("#clearHistory").addEventListener("click", () => {
  const confirmed = window.confirm("Clear all logged aircraft, flyover events, daily stats, and raw positions?");
  if (confirmed) post("/api/history/clear");
});
mapZoomRange.addEventListener("input", () => setMapZoom(mapZoomRange.value));
mapZoomNumber.addEventListener("input", () => setMapZoom(mapZoomNumber.value));
document.querySelector("#saveMapZoom").addEventListener("click", async () => {
  settingsResult.textContent = "Saving...";
  try {
    const response = await fetch("/api/settings/map-zoom", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ map_zoom_level: Number(mapZoomNumber.value) }),
    });
    const payload = await response.json();
    if (!response.ok || payload.ok === false) throw new Error(payload.detail || "Save failed");
    setMapZoom(payload.map_zoom_level);
    settingsResult.textContent = `Map zoom saved at ${payload.map_zoom_level}`;
    await loadStatus();
  } catch (error) {
    settingsResult.textContent = "Map zoom save failed";
  }
});
loadStatus();
setInterval(loadStatus, 5000);
