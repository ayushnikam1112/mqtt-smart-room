# MQTT Smart Room Monitoring (CNL Mini Project)

Simulated IoT sensors publish data over MQTT (Mosquitto broker). A dashboard shows
live data, raises alerts, and controls a fan. QoS levels are tested under packet loss.

## Setup
```bash
sudo apt install mosquitto mosquitto-clients     # Linux (Windows: install from mosquitto.org)
pip install -r requirements.txt
sudo systemctl start mosquitto                   # or run: mosquitto -v
```
## Run (each in its own terminal)
```bash
python fan.py
python app.py          # web dashboard -> open http://localhost:5000
python publisher.py temp 1
python publisher.py humidity 1
python publisher.py light 1
```
(`subscriber.py` is an alternative desktop dashboard using matplotlib; run either `app.py` or `subscriber.py`, not both.)

## Tests
1. Normal: all data appears on the dashboard.
2. High temp: wait for a spike -> ALERT + FAN ON (see alerts.log).
3. Last Will: kill a publisher with `kill -9 <pid>` -> status shows `offline` after ~15 s.
4. QoS under loss (Linux):
```bash
sudo tc qdisc add dev lo root netem loss 20%
python qos_test.py 0 ; python qos_test.py 1 ; python qos_test.py 2
sudo tc qdisc del dev lo root
```
   Note: MQTT runs on TCP, so TCP retransmits lost packets and even QoS 0 often arrives (just delayed).
   Compare delay and packets per message in Wireshark; try higher loss (e.g. 40%) to stress it.
5. Wireshark: capture on loopback (`lo`), filter `mqtt` or `tcp.port==1883`.
   Find CONNECT, CONNACK, PUBLISH, PUBACK, SUBSCRIBE.
6. Auth test: see mosquitto docs (`mosquitto_passwd`, `allow_anonymous false`).
