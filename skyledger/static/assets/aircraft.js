function fmt(value, suffix = "") {
  if (value === null || value === undefined || value === "") return "--";
  if (typeof value === "number") return `${value.toLocaleString()}${suffix}`;
  return `${value}${suffix}`;
}

function when(value) {
  return value ? new Date(value).toLocaleString() : "--";
}

async function loadAircraft() {
  const hex = decodeURIComponent(window.location.pathname.split("/").pop() || "");
  document.querySelector("#aircraftHex").textContent = hex || "--";
  const rows = document.querySelector("#aircraftRows");
  try {
    const response = await fetch(`/api/aircraft/${encodeURIComponent(hex)}`);
    if (!response.ok) throw new Error("missing");
    const payload = await response.json();
    const aircraft = payload.aircraft || {};
    document.querySelector("#aircraftHex").textContent = aircraft.registration || aircraft.hex || hex;
    document.querySelector("#aircraftMeta").textContent = [
      aircraft.hex,
      aircraft.aircraft_type,
      aircraft.operator,
      aircraft.first_seen ? `first seen ${when(aircraft.first_seen)}` : null,
    ].filter(Boolean).join(" | ") || "Local ADS-B aircraft";
    document.querySelector("#aircraftSightings").textContent = fmt(aircraft.total_sightings || 0);
    document.querySelector("#aircraftLowest").textContent = fmt(aircraft.lowest_altitude_ft, " ft");
    document.querySelector("#aircraftClosest").textContent = aircraft.lowest_distance_mi === null || aircraft.lowest_distance_mi === undefined
      ? "--"
      : `${Number(aircraft.lowest_distance_mi).toFixed(2)} mi`;
    rows.innerHTML = (payload.events || []).map((event) => `
      <tr>
        <td>${when(event.seen_at)}</td>
        <td>${event.callsign || "--"}</td>
        <td>${fmt(event.altitude_ft, " ft")}</td>
        <td>${event.distance_mi === null || event.distance_mi === undefined ? "--" : `${Number(event.distance_mi).toFixed(2)} mi`}</td>
        <td>${fmt(event.speed_kt, " kt")}</td>
        <td>${event.event_type || "--"}</td>
      </tr>
    `).join("") || `<tr><td colspan="6">No events logged for this aircraft.</td></tr>`;
  } catch (error) {
    document.querySelector("#aircraftMeta").textContent = "Aircraft has not been logged yet.";
    rows.innerHTML = `<tr><td colspan="6">No events logged for this aircraft.</td></tr>`;
  }
}

loadAircraft();
