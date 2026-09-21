import time
import st7789
from PIL import Image


display = st7789.ST7789(
    port=0,
    cs=1,
    dc=25,
    rst=24,
    width=320,
    height=240,
    rotation=180,
    invert=True,
    backlight=None,
    spi_speed_hz=4_000_000,
)

print("Starting display...")
display.reset()

print("RED")
image = Image.new("RGB", (320, 240), (255, 0, 0))
display.display(image)

time.sleep(5)

print("GREEN")
image = Image.new("RGB", (320, 240), (0, 255, 0))
display.display(image)

time.sleep(5)

print("BLUE")
image = Image.new("RGB", (320, 240), (0, 0, 255))
display.display(image)

time.sleep(5)

print("WHITE")
image = Image.new("RGB", (320, 240), (255, 255, 255))
display.display(image)

time.sleep(5)

print("BLACK")
image = Image.new("RGB", (320, 240), (0, 0, 0))
display.display(image)

while True:
    time.sleep(1)
