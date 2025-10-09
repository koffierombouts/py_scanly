from flask import Flask, Response
from picamera2 import Picamera2
import cv2
from pyzbar.pyzbar import decode
import os
import paho.mqtt.client as mqtt

app = Flask(__name__)

picam2 = Picamera2()
config = picam2.create_preview_configuration()
picam2.configure(config)
picam2.start()

BARCODE_FILE = "barcodes.txt"

MQTT_BROKER = "mqtt.axelpauwels.be"
MQTT_PORT = 4568
MQTT_TOPIC = "studenten"
MQTT_USER = "iotuser"
MQTT_PASS = "iotuser123"

client = mqtt.Client()
client.username_pw_set(MQTT_USER, MQTT_PASS)
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()


def parse_barcode(raw: str):
    if not raw.startswith("S"):
        return None, None, None
    nummer = raw[5:-2]   # '150032'
    check = raw[-2:]     # '70'
    try:
        berekend = int(nummer) % 97
        return nummer, int(check), berekend
    except ValueError:
        return None, None, None


def save_unique_number(nummer: str):
    if not nummer:
        return
    if not os.path.exists(BARCODE_FILE):
        with open(BARCODE_FILE, "w") as f:
            f.write("")
    with open(BARCODE_FILE, "r") as f:
        existing = {line.strip() for line in f}
    if nummer not in existing:
        with open(BARCODE_FILE, "a") as f:
            f.write(nummer + "\n")
        print(f"Nieuwe kaart: {nummer}")

        client.publish(MQTT_TOPIC, nummer)


def generate():
    while True:
        frame = picam2.capture_array()

        # Zwart-wit beeld
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
                    text = f"{nummer} CHECK"
                    save_unique_number(nummer)
                else:
                    text = f"{nummer} NIET CHECK (check {check}, berekend {berekend})"
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
    return Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def index():
    return "<img src='/video'>"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)