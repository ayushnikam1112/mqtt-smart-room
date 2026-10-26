"""Fake actuator (fan). Run: python fan.py  -> reacts to commands on room/fan."""
from common import make_client, BROKER, PORT
import time

def on_connect(client, userdata, *args):
    client.subscribe("room/fan", qos=1)

def on_message(client, userdata, msg):
    print(f"*** FAN is now {msg.payload.decode()} ***")

c = make_client("fan")
c.on_connect = on_connect
c.on_message = on_message
c.connect(BROKER, PORT)
c.loop_forever()
