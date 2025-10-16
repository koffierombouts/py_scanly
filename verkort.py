import cv2, time, threading
import MFRC522, signal
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import os
from flask import Flask, Response
from picamera2 import Picamera2
from pyzbar.pyzbar import decode
from rpi_ws281x import PixelStrip, Color
from dotenv import load_dotenv

# --- MQTT setup ---
MQTT_BROKER = "mqtt.peetermans.dev"
MQTT_PORT = 1884
MQTT_TOPIC = "studenten"
MQTT_USER = "iotuser"
MQTT_PASS = "iotuser123"

client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

def on_connect(client, userdata, flags, rc):
    print("Verbonden met MQTT, status:", rc)
def on_publish(client, userdata, mid):
    print(f"Koppeling gepubliceerd, mid={mid}")

client.on_connect = on_connect
client.on_publish = on_publish

# --- Camera setup ---
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration())
picam2.start()

# --- LED setup ---
LED_COUNT, LED_PIN = 5, 18
strip = PixelStrip(LED_COUNT, LED_PIN)
strip.begin()

def set_led(color, timeout=3):
    strip.setPixelColor(4, color)
    strip.show()
    if timeout:
        threading.Timer(timeout, lambda: set_led(Color(0,0,0), 0)).start()

def set_white_led():
    for i in range(4):
        strip.setPixelColor(i, Color(255, 160, 60))
    strip.show()

# --- Buzzer setup ---
BUZZER_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

def buzz(duration=0.2):
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    time.sleep(duration)
    GPIO.output(BUZZER_PIN, GPIO.LOW)

# --- Flask setup ---
app = Flask(__name__)

last_barcode, last_rfid = None, None
last_barcode_read, last_rfid_read = None, None  # om dubbele scans te vermijden
lock = threading.Lock()
continue_reading = True
running = True

def parse_barcode(data):
    if data.startswith("S"):
        nummer, check = data[5:-2], data[-2:]
        try:
            return nummer if int(nummer) % 97 == int(check) else None
        except:
            pass
    return None

def check_link():
    global last_barcode, last_rfid
    with lock:
        if last_barcode and last_rfid:
            print(f"Koppeling: {last_barcode} - {last_rfid}")
            koppeling = f"{last_barcode};{last_rfid}"
            client.publish(MQTT_TOPIC, koppeling)
            set_led(Color(0,255,0))
            buzz(0.4)  # ✅ lange piep bij succes
            last_barcode, last_rfid = None, None

def generate():
    global last_barcode, running, last_barcode_read
    while running:
        frame = picam2.capture_array()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        barcodes = decode(gray)
        for b in barcodes:
            nummer = parse_barcode(b.data.decode())
            if nummer:
                # check of het een nieuwe barcode is
                if nummer != last_barcode_read:
                    last_barcode_read = nummer
                    with lock: last_barcode = nummer
                    check_link()
            else:
                set_led(Color(255,0,0))  # ❌ rood bij fout
                buzz(0.15)              # korte piep bij fout
            cv2.rectangle(frame, b.rect[:2], 
                          (b.rect[0]+b.rect[2], b.rect[1]+b.rect[3]), 
                          (0,255,0), 2)
        ret, buf = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')

@app.route('/video')
def video(): 
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index(): 
    return "<img src='/video'>"

# --- RFID loop ---
def rfid_loop():
    global last_rfid, last_rfid_read
    r = MFRC522.MFRC522()
    while continue_reading:
        (status, _) = r.MFRC522_Request(r.PICC_REQIDL)
        if status == r.MI_OK:
            (status, uid) = r.MFRC522_SelectTagSN()
            if status == r.MI_OK:
                uid_str = "".join(format(i,'02X') for i in uid)
                if uid_str != last_rfid_read:   # alleen bij nieuwe kaart
                    last_rfid_read = uid_str
                    with lock: last_rfid = uid_str
                    check_link()
        time.sleep(0.2)

# --- Proper afsluiten ---
def end_read(sig, frm):
    global continue_reading, running
    continue_reading = False
    running = False
    picam2.stop()
    GPIO.cleanup()

if __name__ == '__main__':
    set_white_led()
    signal.signal(signal.SIGINT, end_read)
    threading.Thread(target=rfid_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, threaded=True, use_reloader=False)
