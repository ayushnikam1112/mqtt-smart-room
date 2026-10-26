"""Dashboard + alert app. Run: python subscriber.py
Shows live graphs, logs alerts, and commands the fan via topic room/fan."""
import time
from collections import deque
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from common import make_client, BROKER, PORT

TEMP_LIMIT = 35.0
data = {k: deque(maxlen=50) for k in ("temp", "humidity", "light")}
status = {"temp": "?", "humidity": "?", "light": "?"}
fan = {"state": "OFF"}
alerts = deque(maxlen=3)

def log_alert(text):
    line = f"{datetime.now():%H:%M:%S}  {text}"
    print("ALERT:", line)
    alerts.append(line)
    with open("alerts.log", "a") as f:
        f.write(line + "\n")

def on_connect(client, userdata, *args):
    print("Connected to broker")
    client.subscribe([("room/temp", 1), ("room/humidity", 1),
                      ("room/light", 1), ("room/status/#", 1)])

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    if msg.topic.startswith("room/status/"):
        status[msg.topic.split("/")[-1]] = payload
        return
    sensor = msg.topic.split("/")[-1]
    value = float(payload)
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

client = make_client("dashboard")
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, keepalive=30)
client.loop_start()

fig, axes = plt.subplots(3, 1, figsize=(9, 8), sharex=False)
titles = {"temp": "Temperature (C)", "humidity": "Humidity (%)", "light": "Light (lux)"}
colors = {"temp": "red", "humidity": "blue", "light": "orange"}

def update(_):
    for ax, key in zip(axes, data):
        ax.clear()
        ax.plot(list(data[key]), color=colors[key])
        ax.set_title(f"{titles[key]}   [sensor: {status[key]}]")
        if key == "temp":
            ax.axhline(TEMP_LIMIT, color="gray", linestyle="--")
    fig.suptitle(f"Smart Room   FAN: {fan['state']}", fontsize=14,
                 color="green" if fan["state"] == "OFF" else "red")
    if alerts:
        fig.text(0.01, 0.01, "\n".join(alerts), color="red", fontsize=8)

ani = FuncAnimation(fig, update, interval=1000, cache_frame_data=False)
plt.tight_layout(rect=[0, 0.06, 1, 0.95])
plt.show()
client.loop_stop()
