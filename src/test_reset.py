import time
import gpiod
from gpiod.line import Direction, Value

RESET_GPIO = 24

print("Requesting GPIO24...")

request = gpiod.request_lines(
    "/dev/gpiochip0",
    consumer="st7789-reset-test",
    config={
        RESET_GPIO: gpiod.LineSettings(
            direction=Direction.OUTPUT,
            output_value=Value.ACTIVE,
        )
    },
)

print("RESET HIGH")
time.sleep(2)

print("RESET LOW")
request.set_value(RESET_GPIO, Value.INACTIVE)
time.sleep(2)

print("RESET HIGH")
request.set_value(RESET_GPIO, Value.ACTIVE)
time.sleep(2)

print("Done")

request.release()
