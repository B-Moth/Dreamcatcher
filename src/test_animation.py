from time import monotonic, sleep

from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306

from animation import Animation


serial = i2c(
    port=1,
    address=0x3C
)

device = ssd1306(
    serial,
    width=128,
    height=64
)


animation = Animation(
    "assets/animations/HappyCrab.png",
    fps=5
)


last_time = monotonic()

try:

    while True:

        now = monotonic()
        dt = now - last_time
        last_time = now

        animation.update(dt)

        with canvas(device) as draw:
            animation.draw(draw)

        sleep(0.01)

except KeyboardInterrupt:

    device.clear()
