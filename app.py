"""Web dashboard for the MQTT Smart Room.
Run:  python app.py      then open  http://localhost:5000  in your browser.
The page works offline (no external libraries) and refreshes every second."""
import threading
from collections import deque
from datetime import datetime
from flask import Flask, jsonify, Response
from common import make_client, BROKER, PORT

TEMP_LIMIT = 35.0
SENSORS = ("temp", "humidity", "light")

data = {k: deque(maxlen=60) for k in SENSORS}      # last 60 readings per sensor
status = {k: "unknown" for k in SENSORS}           # online / offline (Last Will)
fan = {"state": "OFF"}
alerts = deque(maxlen=20)
conn = {"broker": False}
lock = threading.Lock()


def log_alert(text):
    entry = {"time": datetime.now().strftime("%H:%M:%S"), "text": text}
    alerts.appendleft(entry)
    print("ALERT:", entry["time"], text)
    with open("alerts.log", "a") as f:
        f.write(f'{entry["time"]}  {text}\n')


def on_connect(client, userdata, *args):
    conn["broker"] = True
    print("Connected to broker")
    client.subscribe([("room/temp", 1), ("room/humidity", 1),
                      ("room/light", 1), ("room/status/#", 1)])


def on_disconnect(client, userdata, *args):
    conn["broker"] = False
    print("Disconnected from broker")


def on_message(client, userdata, msg):
    payload = msg.payload.decode(errors="ignore")
    with lock:
        if msg.topic.startswith("room/status/"):
            status[msg.topic.split("/")[-1]] = payload
            return
        sensor = msg.topic.split("/")[-1]
        if sensor not in data:
            return
        try:
            value = float(payload)
        except ValueError:
            return
        data[sensor].append(value)
        print(f"{msg.topic} = {value}")
        if sensor == "temp":
            if value > TEMP_LIMIT and fan["state"] == "OFF":
                fan["state"] = "ON"
                client.publish("room/fan", "ON", qos=1, retain=True)
                log_alert(f"Temperature {value}C > {TEMP_LIMIT}C -> FAN ON")
            elif value <= TEMP_LIMIT - 2 and fan["state"] == "ON":
                fan["state"] = "OFF"
                client.publish("room/fan", "OFF", qos=1, retain=True)
                log_alert(f"Temperature back to {value}C -> FAN OFF")


client = make_client("web-dashboard")
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.connect_async(BROKER, PORT, keepalive=30)    # keeps retrying if broker is down
client.loop_start()

app = Flask(__name__)


@app.route("/api/state")
def api_state():
    with lock:
        return jsonify({
            "data": {k: list(v) for k, v in data.items()},
            "status": status, "fan": fan["state"], "limit": TEMP_LIMIT,
            "alerts": list(alerts), "broker": conn["broker"],
        })


@app.route("/")
def index():
    return Response(PAGE, mimetype="text/html")


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MQTT Smart Room Dashboard</title>
<style>
  :root { --bg:#f3f6fb; --card:#fff; --ink:#1b2430; --mute:#6b7785; --line:#e3e8ef;
          --temp:#e5484d; --hum:#2f6fed; --light:#e69100; --ok:#1e9e55; --bad:#e5484d; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:"Segoe UI",Roboto,Arial,sans-serif; background:var(--bg); color:var(--ink); }
  header { background:#1f3a93; color:#fff; padding:14px 24px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; }
  header h1 { font-size:20px; margin:0; font-weight:600; }
  .pill { padding:4px 12px; border-radius:999px; font-size:13px; font-weight:600; background:rgba(255,255,255,.18); }
  .pill.ok { background:#1e9e55; } .pill.bad { background:#e5484d; }
  main { max-width:1100px; margin:0 auto; padding:20px; }
  .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:16px; margin-bottom:16px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px; }
  .card h3 { margin:0 0 6px; font-size:13px; color:var(--mute); text-transform:uppercase; letter-spacing:.05em; font-weight:600; }
  .big { font-size:38px; font-weight:700; line-height:1.1; }
  .unit { font-size:16px; color:var(--mute); font-weight:500; margin-left:3px; }
  .sub { font-size:13px; color:var(--mute); margin-top:6px; display:flex; align-items:center; gap:6px; }
  .dot { width:9px; height:9px; border-radius:50%; background:#b5bcc6; display:inline-block; }
  .dot.online { background:var(--ok); } .dot.offline { background:var(--bad); }
  .fan.on { background:#fdeaea; border-color:#f3b4b6; } .fan.on .big { color:var(--bad); }
  .fan.off .big { color:var(--ok); }
  .spin { display:inline-block; font-size:28px; margin-right:6px; }
  .fan.on .spin { animation:rot 0.7s linear infinite; }
  @keyframes rot { to { transform:rotate(360deg); } }
  .charts { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:16px; margin-bottom:16px; }
  canvas { width:100%; height:180px; display:block; }
  .alerts ul { list-style:none; margin:0; padding:0; max-height:200px; overflow:auto; }
  .alerts li { padding:8px 10px; border-left:4px solid var(--bad); background:#fff5f5; margin-bottom:6px; border-radius:4px; font-size:14px; }
  .alerts li.clear { border-color:var(--ok); background:#f2fbf6; }
  .alerts li b { color:var(--mute); margin-right:8px; font-weight:600; }
  .empty { color:var(--mute); font-size:14px; }
  footer { text-align:center; color:var(--mute); font-size:12px; padding:10px; }
</style></head>
<body>
<header>
  <h1>MQTT Smart Room Monitoring</h1>
  <span id="broker" class="pill bad">Broker: connecting...</span>
</header>
<main>
  <div class="cards">
    <div class="card"><h3>Temperature</h3><div class="big" id="v-temp">--<span class="unit">&deg;C</span></div>
      <div class="sub"><span class="dot" id="d-temp"></span><span id="s-temp">sensor: unknown</span></div></div>
    <div class="card"><h3>Humidity</h3><div class="big" id="v-humidity">--<span class="unit">%</span></div>
      <div class="sub"><span class="dot" id="d-humidity"></span><span id="s-humidity">sensor: unknown</span></div></div>
    <div class="card"><h3>Light</h3><div class="big" id="v-light">--<span class="unit">lux</span></div>
      <div class="sub"><span class="dot" id="d-light"></span><span id="s-light">sensor: unknown</span></div></div>
    <div class="card fan off" id="fancard"><h3>Fan (actuator)</h3>
      <div class="big"><span class="spin">&#10051;</span><span id="fanstate">OFF</span></div>
      <div class="sub">turns ON above <span id="limit">35</span>&deg;C</div></div>
  </div>
  <div class="charts">
    <div class="card"><h3>Temperature (&deg;C)</h3><canvas id="c-temp"></canvas></div>
    <div class="card"><h3>Humidity (%)</h3><canvas id="c-humidity"></canvas></div>
    <div class="card"><h3>Light (lux)</h3><canvas id="c-light"></canvas></div>
  </div>
  <div class="card alerts"><h3>Alerts</h3><ul id="alerts"><li class="empty" style="border:none;background:none">No alerts yet</li></ul></div>
</main>
<footer>Data flows: sensors &rarr; MQTT broker (Mosquitto, port 1883) &rarr; this dashboard</footer>
<script>
const COLORS = {temp:"#e5484d", humidity:"#2f6fed", light:"#e69100"};
const UNITS = {temp:"\u00b0C", humidity:"%", light:"lux"};
let LIMIT = 35;

function draw(id, vals, color, limit) {
  const cv = document.getElementById("c-" + id), dpr = window.devicePixelRatio || 1;
  const W = cv.clientWidth, H = cv.clientHeight;
  cv.width = W * dpr; cv.height = H * dpr;
  const g = cv.getContext("2d"); g.scale(dpr, dpr); g.clearRect(0, 0, W, H);
  const pl = 42, pr = 10, pt = 10, pb = 20;
  let lo = Math.min(...vals, limit ?? Infinity), hi = Math.max(...vals, limit ?? -Infinity);
  if (!vals.length) { lo = 0; hi = 1; }
  if (hi - lo < 1) { hi += 1; lo -= 1; }
  const pad = (hi - lo) * 0.1; lo -= pad; hi += pad;
  const X = i => pl + (vals.length < 2 ? 0 : i * (W - pl - pr) / (vals.length - 1));
  const Y = v => pt + (hi - v) * (H - pt - pb) / (hi - lo);
  g.strokeStyle = "#e3e8ef"; g.fillStyle = "#6b7785"; g.font = "11px sans-serif"; g.lineWidth = 1;
  for (let k = 0; k <= 4; k++) {
    const v = lo + (hi - lo) * k / 4, y = Y(v);
    g.beginPath(); g.moveTo(pl, y); g.lineTo(W - pr, y); g.stroke();
    g.fillText(v.toFixed(0), 4, y + 4);
  }
  if (limit != null) {
    g.setLineDash([6, 4]); g.strokeStyle = "#8a94a3";
    g.beginPath(); g.moveTo(pl, Y(limit)); g.lineTo(W - pr, Y(limit)); g.stroke(); g.setLineDash([]);
    g.fillStyle = "#8a94a3"; g.fillText("limit " + limit, W - pr - 62, Y(limit) - 4);
  }
  if (!vals.length) { g.fillStyle = "#6b7785"; g.fillText("waiting for data...", pl + 10, H / 2); return; }
  g.strokeStyle = color; g.lineWidth = 2; g.beginPath();
  vals.forEach((v, i) => i ? g.lineTo(X(i), Y(v)) : g.moveTo(X(i), Y(v))); g.stroke();
  g.fillStyle = color; g.beginPath(); g.arc(X(vals.length - 1), Y(vals[vals.length - 1]), 4, 0, 7); g.fill();
}

async function refresh() {
  try {
    const r = await fetch("/api/state"); const s = await r.json();
    LIMIT = s.limit; document.getElementById("limit").textContent = LIMIT;
    const b = document.getElementById("broker");
    b.textContent = s.broker ? "Broker: connected" : "Broker: disconnected"; b.className = "pill " + (s.broker ? "ok" : "bad");
    for (const k of ["temp", "humidity", "light"]) {
      const v = s.data[k], last = v.length ? v[v.length - 1].toFixed(1) : "--";
      document.getElementById("v-" + k).innerHTML = last + '<span class="unit">' + UNITS[k] + "</span>";
      const st = s.status[k];
      document.getElementById("s-" + k).textContent = "sensor: " + st;
      document.getElementById("d-" + k).className = "dot " + (st === "online" ? "online" : st === "offline" ? "offline" : "");
      draw(k, v, COLORS[k], k === "temp" ? LIMIT : null);
    }
    document.getElementById("fanstate").textContent = s.fan;
    document.getElementById("fancard").className = "card fan " + s.fan.toLowerCase();
    const ul = document.getElementById("alerts");
    ul.innerHTML = s.alerts.length ? s.alerts.map(a =>
      '<li class="' + (a.text.includes("FAN OFF") ? "clear" : "") + '"><b>' + a.time + "</b>" + a.text + "</li>").join("")
      : '<li class="empty" style="border:none;background:none">No alerts yet</li>';
  } catch (e) {
    const b = document.getElementById("broker"); b.textContent = "Dashboard server unreachable"; b.className = "pill bad";
  }
}
refresh(); setInterval(refresh, 1000);
</script></body></html>
"""

if __name__ == "__main__":
    print("Open http://localhost:5000 in your browser")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
