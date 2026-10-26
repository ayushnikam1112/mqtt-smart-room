"""Shared settings and helper for all MQTT programs."""
import paho.mqtt.client as mqtt

BROKER = "localhost"   # change to broker laptop's IP if using 2 laptops
PORT = 1883            # default MQTT port (runs over TCP)

def make_client(name):
    """Create an MQTT client (works with paho-mqtt 1.x and 2.x)."""
    try:
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=name)
    except AttributeError:
        return mqtt.Client(client_id=name)
