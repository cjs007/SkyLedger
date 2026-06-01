function fmt(value, suffix = "") {
  if (value === null || value === undefined || value === "") return "--";
  if (typeof value === "number") return `${value.toLocaleString()}${suffix}`;
  return `${value}${suffix}`;
}

function when(value) {
  return value ? new Date(value).toLocaleString() : "--";
}

function flags(row) {
  const list = [];
  if (row.is_new_aircraft) list.push("new");
  if (row.is_new_lowest) list.push("lowest");
  if (row.was_alerted) list.push("alerted");
  if (row.was_revealed) list.push("revealed");
  return list.join(", ") || "--";
}

async function loadHistory() {
  const rows = document.querySelector("#historyRows");
  try {
    const response = await fetch("/api/history?limit=300");
    const events = await response.json();
    rows.innerHTML = events.map((event) => `
      <tr>
        <td>${when(event.seen_at)}</td>
        <td><a href="/aircraft/${encodeURIComponent(event.hex)}">${event.callsign || event.hex || "--"}</a></td>
        <td>${fmt(event.altitude_ft, " ft")}</td>
        <td>${event.distance_mi === null || event.distance_mi === undefined ? "--" : `${Number(event.distance_mi).toFixed(2)} mi`}</td>
        <td>${fmt(event.speed_kt, " kt")}</td>
        <td>${[event.registration, event.aircraft_type, event.operator].filter(Boolean).join(" | ") || event.hex || "--"}</td>
        <td>${flags(event)}</td>
      </tr>
    `).join("") || `<tr><td colspan="7">No flyovers logged yet.</td></tr>`;
  } catch (error) {
    rows.innerHTML = `<tr><td colspan="7">Unable to load history.</td></tr>`;
  }
}

loadHistory();
