"""Simulated sensor. Usage: python publisher.py temp|humidity|light [qos]
Publishes a value every 2 seconds to topic room/<sensor>.
Has a Last Will: if it dies, the broker publishes 'offline' for it."""
import sys, time, random
from common import make_client, BROKER, PORT

sensor = sys.argv[1] if len(sys.argv) > 1 else "temp"
qos = int(sys.argv[2]) if len(sys.argv) > 2 else 1

RANGES = {"temp": (28, 3), "humidity": (60, 5), "light": (400, 40)}  # start, step
value, step = RANGES[sensor]

client = make_client(f"sensor-{sensor}")
# Last Will: broker sends this automatically if we disconnect abnormally
client.will_set(f"room/status/{sensor}", "offline", qos=1, retain=True)
client.connect(BROKER, PORT, keepalive=10)
client.loop_start()
client.publish(f"room/status/{sensor}", "online", qos=1, retain=True)
print(f"[{sensor}] started, QoS {qos}. Ctrl+C to stop.")

try:
    while True:
        value += random.uniform(-step, step) / 2
        if sensor == "temp" and random.random() < 0.08:   # occasional heat spike
            value += 8
        if sensor == "temp":
            value = max(20, min(value, 45))
            if value > 36:
                value -= 3     # drift back down
        msg = f"{value:.1f}"
        client.publish(f"room/{sensor}", msg, qos=qos)
        print(f"[{sensor}] published {msg}")
        time.sleep(2)
except KeyboardInterrupt:
    # Clean exit: send offline ourselves (Last Will only fires on abnormal exit)
    client.publish(f"room/status/{sensor}", "offline", qos=1, retain=True).wait_for_publish()
    client.loop_stop(); client.disconnect()
