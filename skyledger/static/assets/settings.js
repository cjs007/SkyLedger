const statusList = document.querySelector("#statusList");
const configList = document.querySelector("#configList");
const testResult = document.querySelector("#testResult");

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

async function post(path) {
  testResult.textContent = "Running...";
  try {
    const response = await fetch(path, { method: "POST" });
    const payload = await response.json();
    testResult.textContent = payload.error || (payload.ok === false ? "Test accepted" : "Test sent");
  } catch (error) {
    testResult.textContent = "Test failed";
  }
}

document.querySelector("#testCountdown").addEventListener("click", () => post("/api/test-countdown"));
document.querySelector("#testDiscord").addEventListener("click", () => post("/api/test-discord"));
loadStatus();
setInterval(loadStatus, 5000);
