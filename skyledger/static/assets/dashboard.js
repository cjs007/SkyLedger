const state = {
  payload: null,
  radarAngle: 0,
  ws: null,
};

const els = {
  clock: document.querySelector("#clock"),
  receiverStatus: document.querySelector("#receiverStatus"),
  lastUpdate: document.querySelector("#lastUpdate"),
  dashboardTitle: document.querySelector("#dashboardTitle"),
  homeName: document.querySelector("#homeName"),
  tar1090Link: document.querySelector("#tar1090Link"),
  liveMode: document.querySelector("#liveMode"),
  countdownMode: document.querySelector("#countdownMode"),
  revealMode: document.querySelector("#revealMode"),
  radarCanvas: document.querySelector("#radarCanvas"),
  closestTitle: document.querySelector("#closestTitle"),
  rangeLabel: document.querySelector("#rangeLabel"),
  liveCount: document.querySelector("#liveCount"),
  closestDistance: document.querySelector("#closestDistance"),
  statFlyovers: document.querySelector("#statFlyovers"),
  statNew: document.querySelector("#statNew"),
  statRepeat: document.querySelector("#statRepeat"),
  statLowest: document.querySelector("#statLowest"),
  closestCallsign: document.querySelector("#closestCallsign"),
  closestAltitude: document.querySelector("#closestAltitude"),
  closestSpeed: document.querySelector("#closestSpeed"),
  closestHeading: document.querySelector("#closestHeading"),
  activeCount: document.querySelector("#activeCount"),
  nearbyList: document.querySelector("#nearbyList"),
  recentEvents: document.querySelector("#recentEvents"),
  countdownNumber: document.querySelector("#countdownNumber"),
  countdownCallsign: document.querySelector("#countdownCallsign"),
  countdownDirection: document.querySelector("#countdownDirection"),
  countdownDistance: document.querySelector("#countdownDistance"),
  countdownSpeed: document.querySelector("#countdownSpeed"),
  revealCallsign: document.querySelector("#revealCallsign"),
  revealAltitude: document.querySelector("#revealAltitude"),
  revealBadge: document.querySelector("#revealBadge"),
  revealDistance: document.querySelector("#revealDistance"),
  revealSpeed: document.querySelector("#revealSpeed"),
  revealHeading: document.querySelector("#revealHeading"),
  revealVertical: document.querySelector("#revealVertical"),
  revealAircraft: document.querySelector("#revealAircraft"),
  revealHistory: document.querySelector("#revealHistory"),
  revealHex: document.querySelector("#revealHex"),
  revealRoute: document.querySelector("#revealRoute"),
  revealTimer: document.querySelector("#revealTimer"),
};

function fmtNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return Number(value).toLocaleString();
}

function fmtAltitude(value) {
  return value === null || value === undefined ? "--" : `${fmtNumber(value)} ft`;
}

function fmtDistance(value) {
  return value === null || value === undefined ? "--" : `${Number(value).toFixed(2)} mi`;
}

function fmtSpeed(value) {
  return value === null || value === undefined ? "--" : `${fmtNumber(value)} kt`;
}

function fmtHeading(value) {
  return value === null || value === undefined ? "--" : `${Math.round(value)} deg`;
}

function label(ac) {
  return ac?.callsign || ac?.hex || "Unknown";
}

function setMode(mode) {
  for (const panel of [els.liveMode, els.countdownMode, els.revealMode]) {
    panel.classList.remove("active");
  }
  if (mode === "countdown") els.countdownMode.classList.add("active");
  else if (mode === "reveal") els.revealMode.classList.add("active");
  else els.liveMode.classList.add("active");
}

function updateClock() {
  els.clock.textContent = new Date().toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });
}

function render(payload) {
  state.payload = payload;
  const config = payload.config || {};
  const status = payload.status || {};
  const stats = payload.stats_today || {};
  const closest = payload.closest_aircraft;

  document.title = config.dashboard_title || "SkyLedger";
  els.dashboardTitle.textContent = config.dashboard_title || "SkyLedger";
  els.homeName.textContent = config.home_name || "Gazebo Flight Command Center";
  els.tar1090Link.href = config.tar1090_url || "http://localhost/tar1090/";
  els.rangeLabel.textContent = `${Number(config.guess_trigger_radius_miles || 3).toFixed(1)} mi`;

  const online = Boolean(status.receiver_online);
  els.receiverStatus.textContent = online ? "Receiver online" : "Receiver offline";
  els.receiverStatus.className = `status-pill ${online ? "online" : "offline"}`;
  els.lastUpdate.textContent = status.last_poll_at ? `Updated ${new Date(status.last_poll_at).toLocaleTimeString()}` : "Waiting for data";

  setMode(payload.mode);
  renderLive(payload, stats, closest);
  if (payload.mode === "countdown") renderCountdown(payload.focus || {});
  if (payload.mode === "reveal") renderReveal(payload.focus || {});
}

function renderLive(payload, stats, closest) {
  const live = payload.live_aircraft || [];
  els.liveCount.textContent = live.length;
  els.closestDistance.textContent = closest ? fmtDistance(closest.distance_mi) : "--";
  els.closestTitle.textContent = closest ? label(closest) : "Scanning";
  els.statFlyovers.textContent = fmtNumber(stats.total_flyovers || 0);
  els.statNew.textContent = fmtNumber(stats.new_aircraft || 0);
  els.statRepeat.textContent = fmtNumber(stats.repeat_aircraft || 0);
  els.statLowest.textContent = fmtAltitude(stats.lowest_altitude_ft);
  els.closestCallsign.textContent = closest ? label(closest) : "No aircraft nearby";
  els.closestAltitude.textContent = closest ? fmtAltitude(closest.altitude_ft) : "--";
  els.closestSpeed.textContent = closest ? fmtSpeed(closest.speed_kt) : "--";
  els.closestHeading.textContent = closest ? fmtHeading(closest.heading) : "--";
  els.activeCount.textContent = `${payload.active_count || 0} active`;

  els.nearbyList.innerHTML = live.slice(0, 8).map((ac) => `
    <a class="aircraft-item" href="/aircraft/${encodeURIComponent(ac.hex)}">
      <strong>${escapeHtml(label(ac))}</strong>
      <span>${fmtDistance(ac.distance_mi)}</span>
      <span>${fmtAltitude(ac.altitude_ft)}</span>
      <span>${fmtSpeed(ac.speed_kt)}</span>
    </a>
  `).join("") || `<div class="event-item"><strong>No aircraft in range</strong><span>Standing by</span></div>`;

  els.recentEvents.innerHTML = (payload.recent_events || []).slice(0, 5).map((event) => `
    <a class="event-item" href="/aircraft/${encodeURIComponent(event.hex)}">
      <strong>${escapeHtml(event.callsign || event.hex)}</strong>
      <span>${fmtAltitude(event.altitude_ft)} at ${fmtDistance(event.distance_mi)}</span>
    </a>
  `).join("") || `<div class="event-item"><strong>No flyovers logged</strong><span>History will appear here</span></div>`;
}

function renderCountdown(focus) {
  els.countdownNumber.textContent = Math.max(0, focus.seconds_remaining || 0);
  els.countdownCallsign.textContent = focus.callsign || focus.hex || "Inbound aircraft";
  els.countdownDirection.textContent = focus.direction || "Approaching";
  els.countdownDistance.textContent = fmtDistance(focus.distance_mi);
  els.countdownSpeed.textContent = fmtSpeed(focus.speed_kt);
}

function renderReveal(focus) {
  els.revealCallsign.textContent = focus.callsign || focus.hex || "Unknown";
  els.revealAltitude.textContent = fmtAltitude(focus.altitude_ft);
  const badges = [];
  if (focus.is_new_aircraft) badges.push("New aircraft over SkyLedger");
  if (focus.is_new_lowest) badges.push("Lowest pass recorded");
  if (!badges.length) badges.push(`You've seen this aircraft ${fmtNumber(focus.total_sightings || 1)} time(s)`);
  els.revealBadge.textContent = badges.join(" | ");
  els.revealDistance.textContent = fmtDistance(focus.distance_mi);
  els.revealSpeed.textContent = fmtSpeed(focus.speed_kt);
  els.revealHeading.textContent = fmtHeading(focus.heading);
  els.revealVertical.textContent = focus.vertical_rate_fpm === null || focus.vertical_rate_fpm === undefined ? "--" : `${fmtNumber(focus.vertical_rate_fpm)} fpm`;
  els.revealAircraft.textContent = [focus.registration, focus.aircraft_type, focus.operator].filter(Boolean).join(" | ") || "Local ADS-B only";
  els.revealHistory.textContent = `Total sightings ${fmtNumber(focus.total_sightings || 1)}; lowest ${fmtAltitude(focus.lowest_altitude_ft)}`;
  els.revealHex.textContent = `hex ${focus.hex || "--"}`;
  els.revealRoute.textContent = focus.route_from && focus.route_to ? `${focus.route_from} to ${focus.route_to}` : "Route unknown";
  els.revealTimer.textContent = `${Math.max(0, focus.seconds_remaining || 0)}s`;
}

function drawRadar() {
  const canvas = els.radarCanvas;
  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;
  const width = Math.max(320, Math.floor(rect.width * scale));
  const height = Math.max(320, Math.floor(rect.height * scale));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }

  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.min(width, height) * 0.44;
  ctx.clearRect(0, 0, width, height);
  ctx.lineWidth = 1 * scale;
  ctx.strokeStyle = "rgba(110, 231, 255, 0.2)";
  ctx.fillStyle = "rgba(97, 244, 168, 0.05)";

  for (let ring = 1; ring <= 4; ring += 1) {
    ctx.beginPath();
    ctx.arc(cx, cy, (radius * ring) / 4, 0, Math.PI * 2);
    ctx.stroke();
  }
  for (let spoke = 0; spoke < 12; spoke += 1) {
    const angle = (spoke / 12) * Math.PI * 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius);
    ctx.stroke();
  }

  state.radarAngle = (state.radarAngle + 0.012) % (Math.PI * 2);
  const sweep = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
  sweep.addColorStop(0, "rgba(97, 244, 168, 0.2)");
  sweep.addColorStop(1, "rgba(97, 244, 168, 0)");
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.arc(cx, cy, radius, state.radarAngle - 0.18, state.radarAngle);
  ctx.closePath();
  ctx.fillStyle = sweep;
  ctx.fill();
  ctx.restore();

  ctx.fillStyle = "#61f4a8";
  ctx.beginPath();
  ctx.arc(cx, cy, 5 * scale, 0, Math.PI * 2);
  ctx.fill();

  const aircraft = state.payload?.live_aircraft || [];
  const maxRange = Number(state.payload?.config?.guess_trigger_radius_miles || 3);
  for (const ac of aircraft) {
    if (ac.distance_mi === null || ac.distance_mi === undefined) continue;
    const dist = Math.min(ac.distance_mi / maxRange, 1);
    const angle = ((ac.heading ?? 0) - 90) * (Math.PI / 180);
    const x = cx + Math.cos(angle) * radius * dist;
    const y = cy + Math.sin(angle) * radius * dist;
    ctx.fillStyle = ac.altitude_ft !== null && ac.altitude_ft <= 10000 ? "#61f4a8" : "#6ee7ff";
    ctx.beginPath();
    ctx.arc(x, y, 6 * scale, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "rgba(245, 248, 251, 0.9)";
    ctx.font = `${12 * scale}px system-ui, sans-serif`;
    ctx.fillText(label(ac), x + 10 * scale, y - 10 * scale);
  }

  requestAnimationFrame(drawRadar);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function connect() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  state.ws = new WebSocket(`${protocol}://${window.location.host}/ws/live`);
  state.ws.onmessage = (event) => render(JSON.parse(event.data));
  state.ws.onclose = () => setTimeout(connect, 2000);
  state.ws.onerror = () => state.ws.close();
}

async function pollFallback() {
  if (!state.payload || !state.ws || state.ws.readyState !== WebSocket.OPEN) {
    try {
      const response = await fetch("/api/aircraft/live");
      render(await response.json());
    } catch {
      // The status pill already shows stale/offline state.
    }
  }
  setTimeout(pollFallback, 5000);
}

updateClock();
setInterval(updateClock, 1000);
connect();
pollFallback();
drawRadar();
