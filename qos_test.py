"""QoS comparison. Usage: python qos_test.py <qos> [count]
Sends <count> messages and reports how many were received.
Run it with packet loss enabled (see README) for qos 0, 1, 2."""
import sys, time
from common import make_client, BROKER, PORT

qos = int(sys.argv[1]); count = int(sys.argv[2]) if len(sys.argv) > 2 else 100
received = set()

def on_connect(client, userdata, *args):
    client.subscribe(f"qostest/{qos}", qos=qos)
def on_message(client, userdata, msg):
    received.add(int(msg.payload))

sub = make_client(f"qos-sub-{qos}"); sub.on_connect = on_connect; sub.on_message = on_message
sub.connect(BROKER, PORT); sub.loop_start(); time.sleep(1)

pub = make_client(f"qos-pub-{qos}"); pub.connect(BROKER, PORT); pub.loop_start()
start = time.time()
for i in range(count):
    pub.publish(f"qostest/{qos}", str(i), qos=qos)
    time.sleep(0.05)
time.sleep(10)   # allow retransmissions to finish
print(f"QoS {qos}: sent {count}, received {len(received)}, "
      f"lost {count-len(received)}  ({time.time()-start:.1f}s)")
pub.loop_stop(); sub.loop_stop()
