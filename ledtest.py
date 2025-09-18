import time
from rpi_ws281x import PixelStrip, Color

LED_COUNT = 5        # aantal leds
LED_PIN = 18         # GPIO pin 18 (PWM)
LED_FREQ_HZ = 800000 # LED signaal freq
LED_DMA = 10         # DMA kanaal
LED_BRIGHTNESS = 50
LED_CHANNEL = 0

strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, False, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

status = "red"

# Warm wit
warm_white = Color(255, 160, 60)

# Reset alle leds
for i in range(LED_COUNT):
    strip.setPixelColor(i, Color(0, 0, 0))

# Leds 0–3 warm wit
for i in range(4):
    strip.setPixelColor(i, warm_white)

# Led 4 afhankelijk van status
if status == "groen":
    strip.setPixelColor(4, Color(0, 255, 0))
else:
    strip.setPixelColor(4, Color(255, 0, 0))

# Led 5 uit
strip.setPixelColor(5, Color(0, 0, 0))

strip.show()