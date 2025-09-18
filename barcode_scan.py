from picamera2 import Picamera2
from pyzbar.pyzbar import decode
import time

def parse_barcode(raw):
    """
    Neemt bv. 'S000015003270'
    en geeft nummer + verificatie terug
    """
    if not raw.startswith("S"):
        return None, None

    nummer = raw[5:-2]   # '150032'
    check = raw[-2:]     # '70'

    # Bereken verificatie (mod 97)
    berekend = int(nummer) % 97

    return nummer, int(check), berekend

picam2 = Picamera2()
config = picam2.create_preview_configuration()
picam2.configure(config)
picam2.start()

try:
    while True:
        frame = picam2.capture_array()
        barcodes = decode(frame)

        for barcode in barcodes:
            data = barcode.data.decode('utf-8')
            nummer, check, berekend = parse_barcode(data)

            if nummer:
                print(f"Nummer: {nummer} | Check: {check} | Berekend: {berekend}")
                if check == berekend:
                    print("Verificatie klopt")
                else:
                    print("Verificatie klopt niet")

        time.sleep(0.1)

finally:
    picam2.stop()