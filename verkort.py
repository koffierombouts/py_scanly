import cv2, time, threading, signal, os
import MFRC522, paho.mqtt.client as mqtt, RPi.GPIO as GPIO
from flask import Flask, Response
from picamera2 import Picamera2
from pyzbar.pyzbar import decode
from rpi_ws281x import PixelStrip, Color
from dotenv import load_dotenv

# --- Load environment variables ---
load_dotenv()

# --- MQTT setup ---
load_dotenv() 
MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC")
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASS = os.getenv("MQTT_PASS")

print(f"broker: {MQTT_BROKER}\nport: {MQTT_PORT}\ntopic: {MQTT_TOPIC}\nuser: {MQTT_USER}\npass: {MQTT_PASS}")

client = mqtt.Client()
if MQTT_USER and MQTT_PASS:
    client.username_pw_set(MQTT_USER, MQTT_PASS)

def on_connect(client, userdata, flags, rc):
    print("Verbonden met MQTT, status:", rc)

def on_publish(client, userdata, mid):
    print(f"Koppeling gepubliceerd, mid={mid}")

client.on_connect = on_connect
client.on_publish = on_publish
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

# --- Camera setup ---
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration())
picam2.start()

# --- LED setup ---
# 1 LED voor camera-belichting (warm wit)
LED_COUNT_CAM, LED_PIN_CAM = 1, 13
# 4 LEDs, maar we gebruiken deze strip enkel als status-indicator (alle tegelijk zelfde kleur)
LED_COUNT_STATUS, LED_PIN_STATUS = 4, 18

strip_cam = PixelStrip(LED_COUNT_CAM, LED_PIN_CAM)
strip_cam.begin()

strip_status = PixelStrip(LED_COUNT_STATUS, LED_PIN_STATUS)
strip_status.begin()

def set_status_led(color, timeout=3):
    """Zet alle status-leds op een bepaalde kleur en reset na timeout."""
    for i in range(LED_COUNT_STATUS):
        strip_status.setPixelColor(i, color)
    strip_status.show()
    if timeout:
        threading.Timer(timeout, lambda: set_status_led(Color(0, 0, 0), 0)).start()

def set_camera_led(on=True):
    """Laat de camera-LED (warm wit) constant branden of uitgaan."""
    color = Color(255, 160, 60) if on else Color(0, 0, 0)
    for i in range(LED_COUNT_CAM):
        strip_cam.setPixelColor(i, color)
    strip_cam.show()

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
last_barcode_read, last_rfid_read = None, None
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
            set_status_led(Color(0, 255, 0))  # ✅ groen bij succes
            buzz(0.4)
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
                if nummer != last_barcode_read:
                    last_barcode_read = nummer
                    with lock: last_barcode = nummer
                    check_link()
            else:
                set_status_led(Color(255, 0, 0))  # ❌ rood bij fout
                buzz(0.15)
            x, y, w, h = b.rect
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0,255,0), 2)
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
                uid_str = "".join(format(i, '02X') for i in uid)
                if uid_str != last_rfid_read:
                    last_rfid_read = uid_str
                    with lock: last_rfid = uid_str
                    check_link()
        time.sleep(0.2)

# --- Proper afsluiten ---
def end_read(sig, frm):
    global continue_reading, running
    continue_reading = False
    running = False
    set_camera_led(False)
    set_status_led(Color(0, 0, 0), 0)
    picam2.stop()
    GPIO.cleanup()

if __name__ == '__main__':
    set_camera_led(True)  # altijd warm wit aan voor camera
    signal.signal(signal.SIGINT, end_read)
    threading.Thread(target=rfid_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, threaded=True, use_reloader=False)
