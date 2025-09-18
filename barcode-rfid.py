from flask import Flask, Response
from picamera2 import Picamera2
import cv2
from pyzbar.pyzbar import decode
import os
import paho.mqtt.client as mqtt
import MFRC522
import signal
import threading
import time
import ssl

app = Flask(__name__)

picam2 = Picamera2()
config = picam2.create_preview_configuration()
picam2.configure(config)
picam2.start()

LINK_FILE = "barcode_rfid_links.txt"

MQTT_BROKER = "mqtt.axelpauwels.be"
MQTT_PORT = 4568
MQTT_TOPIC = "studenten"
MQTT_USER = "iotuser"
MQTT_PASS = "iotuser123"

client = mqtt.Client()
client.username_pw_set(MQTT_USER, MQTT_PASS)
client = mqtt.Client()
client.username_pw_set(MQTT_USER, MQTT_PASS)

client.tls_set(
    ca_certs="/etc/ssl/certs/ca-certificates.crt",
    certfile=None,
    keyfile=None,
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)
client.tls_insecure_set(False)

client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

last_barcode = None
last_barcode_time = 0
last_rfid = None
last_rfid_time = 0
lock = threading.Lock()

def on_connect(client, userdata, flags, rc):
    print("🔌 Verbinding status:", rc)  # 0 = succes

def on_publish(client, userdata, mid):
    print(f"📤 Publicatie gelukt, mid={mid}")

client.on_connect = on_connect
client.on_publish = on_publish

def resetLeds():
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 0))

def warmWitteLeds():
    for i in range(4):
        strip.setPixelColor(i, warm_white)


def parse_barcode(raw: str):
    if not raw.startswith("S"):
        return None, None, None
    nummer = raw[5:-2]
    check = raw[-2:]
    try:
        berekend = int(nummer) % 97
        return nummer, int(check), berekend
    except ValueError:
        return None, None, None

def save_link(barcode, rfid):
    if os.path.exists(LINK_FILE):
        with open(LINK_FILE, "r") as f:
            existing = {line.strip() for line in f}
    else:
        existing = set()

    line = f"{barcode};{rfid}"
    if line not in existing:
        with open(LINK_FILE, "a") as f:
            f.write(line + "\n")
        print(f"Koppeling gemaakt: {line}")
        client.publish(MQTT_TOPIC, line)

def check_link():
    global last_barcode, last_barcode_time, last_rfid, last_rfid_time
    with lock:
        if last_barcode and last_rfid:
            if abs(last_barcode_time - last_rfid_time) <= 3:
                save_link(last_barcode, last_rfid)
                last_barcode = None
                last_rfid = None

def generate():
    global last_barcode, last_barcode_time
    while True:
        frame = picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        barcodes = decode(frame)
        for barcode in barcodes:
            x, y, w, h = barcode.rect
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

            data = barcode.data.decode("utf-8")
            nummer, check, berekend = parse_barcode(data)

            if nummer:
                if check == berekend:
                    text = f"{nummer} OK"
                    with lock:
                        last_barcode = nummer
                        last_barcode_time = time.time()
                    check_link()
                else:
                    text = f"{nummer} FOUT (check {check}, berekend {berekend})"
            else:
                text = f"{data} ???"

            cv2.putText(frame, text, (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video')
def video():
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return "<img src='/video'>"

continue_reading = True

def uidToString(uid):
    return "".join(format(i, '02X') for i in uid)

def end_read(signal, frame):
    global continue_reading
    continue_reading = False

def rfid_loop():
    global last_rfid, last_rfid_time
    MIFAREReader = MFRC522.MFRC522()
    while continue_reading:
        (status, TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)
        if status == MIFAREReader.MI_OK:
            (status, uid) = MIFAREReader.MFRC522_SelectTagSN()
            if status == MIFAREReader.MI_OK:
                rfid_code = uidToString(uid)
                print(f"RFID gedetecteerd: {rfid_code}")
                with lock:
                    last_rfid = rfid_code
                    last_rfid_time = time.time()
                check_link()
        time.sleep(0.2)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, end_read)
    threading.Thread(target=rfid_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)