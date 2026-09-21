from datetime import datetime
from time import sleep

from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont

from gpiozero import RotaryEncoder, Button


# ============================================================
# OLED
# ============================================================

serial = i2c(port=1, address=0x3C)

device = ssd1306(
    serial,
    width=128,
    height=64
)


# ============================================================
# EC11
# ============================================================

ENCODER_A = 17
ENCODER_B = 18
BUTTON_PIN = 22

encoder = RotaryEncoder(
    a=ENCODER_A,
    b=ENCODER_B,
    max_steps=0
)

button = Button(
    BUTTON_PIN,
    pull_up=True,
    bounce_time=0.05
)


# ============================================================
# FONTS
# ============================================================

font_time = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    18
)

font_date = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    9
)


# ============================================================
# FRENCH DATE
# ============================================================

weekdays = [
    "Lundi",
    "Mardi",
    "Mercredi",
    "Jeudi",
    "Vendredi",
    "Samedi",
    "Dimanche"
]

months = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre"
]


# ============================================================
# PIXEL ART HELPER
# ============================================================

def pixels(draw, x, y, pattern, fill="white"):
    """
    Draw a pixel-art pattern.

    '#' = pixel ON
    '.' = pixel OFF
    """

    for py, row in enumerate(pattern):

        for px, pixel in enumerate(row):

            if pixel == "#":

                draw.point(
                    (x + px, y + py),
                    fill=fill
                )


# ============================================================
# CONNECTION ICON
# ============================================================

def draw_connection(draw, x, y, connected=True):

    if connected:

        pattern = [
            "........",
            "..####..",
            ".#....#.",
            "#......#",
            "........",
            "..####..",
            ".#....#.",
            "........",
            "...##...",
            "...##..."
        ]

    else:

        pattern = [
            "#..........#",
            ".#........#.",
            "..#.####.#..",
            "...#....#...",
            "..#.#..#.#..",
            ".....##.....",
            "....####....",
            "...##..##...",
            "...#....#...",
            "..#..##..#..",
            ".#...##...#.."
        ]

    pixels(
        draw,
        x,
        y,
        pattern
    )


# ============================================================
# PLUS ICON
# ============================================================

def draw_plus(draw, x, y):

    pattern = [
        ".......##........",
        ".......##........",
        ".......##........",
        ".......##........",
        "...##########....",
        "...##########....",
        ".......##........",
        ".......##........",
        ".......##........",
        ".......##........"
    ]

    pixels(
        draw,
        x,
        y,
        pattern
    )


# ============================================================
# GEAR ICON
# ============================================================

def draw_gear(draw, x, y):

    pattern = [
        "......###......",
        "..##.#...#.##..",
        ".#..##...##..#.",
        ".#...........#.",
        "..#.........#..",
        ".##...#.#...##.",
        "#....#...#....#",
        "#....#...#....#",
        ".##...#.#...##.",
        "..#.........#..",
        ".#...........#.",
        ".#..##...##..#.",
        "..##.#...#.##..",
        "......###......"
    ]

    pixels(
        draw,
        x,
        y,
        pattern
    )


# ============================================================
# ICON DEFINITIONS
#
# Navigation order:
#
#     CONNECTION → GEAR → PLUS → CONNECTION...
#
# ============================================================

ICONS = [
    {
        "name": "connection",
        "pattern": [
            "#..........#",
            ".#........#.",
            "..#.####.#..",
            "...#....#...",
            "..#.#..#.#..",
            ".....##.....",
            "....####....",
            "...##..##...",
            "...#....#...",
            "..#..##..#..",
            ".#...##...#.."
        ],
        "x": 5,
        "y": 4
    },

    {
        "name": "gear",
        "pattern": [
            "......###......",
            "..##.#...#.##..",
            ".#..##...##..#.",
            ".#...........#.",
            "..#.........#..",
            ".##...#.#...##.",
            "#....#...#....#",
            "#....#...#....#",
            ".##...#.#...##.",
            "..#.........#..",
            ".#...........#.",
            ".#..##...##..#.",
            "..##.#...#.##..",
            "......###......"
        ],
        "x": 108,
        "y": 49
    },

    {
        "name": "plus",
        "pattern": [
            ".......##........",
            ".......##........",
            ".......##........",
            ".......##........",
            "...##########....",
            "...##########....",
            ".......##........",
            ".......##........",
            ".......##........",
            ".......##........"
        ],
        "x": 2,
        "y": 48
    }
]


# ============================================================
# SELECTION
# ============================================================

selected = 0

last_encoder_position = encoder.steps


# ============================================================
# DRAW ICON
# ============================================================

def draw_icon(draw, icon, is_selected=False):

    pattern = icon["pattern"]

    x = icon["x"]
    y = icon["y"]

    height = len(pattern)
    width = len(pattern[0])

    # --------------------------------------------------------
    # NORMAL ICON
    # --------------------------------------------------------

    if not is_selected:

        pixels(
            draw,
            x,
            y,
            pattern,
            fill="white"
        )

        return

    # --------------------------------------------------------
    # SELECTED ICON
    #
    # The circle is based on the ACTUAL dimensions of the
    # hardcoded pixel-art pattern.
    #
    # +2 pixels around the icon.
    # --------------------------------------------------------

    center_x = x + (width - 1) / 2
    center_y = y + (height - 1) / 2

    radius = max(width, height) / 2 + 2

    min_x = max(0, int(center_x - radius))
    max_x = min(127, int(center_x + radius))

    min_y = max(0, int(center_y - radius))
    max_y = min(63, int(center_y + radius))

    # --------------------------------------------------------
    # Draw circular white background
    # --------------------------------------------------------

    for py in range(min_y, max_y + 1):

        for px in range(min_x, max_x + 1):

            dx = px - center_x
            dy = py - center_y

            if dx * dx + dy * dy <= radius * radius:

                draw.point(
                    (px, py),
                    fill="white"
                )

    # --------------------------------------------------------
    # Invert the actual pixel art.
    #
    # White icon pixels become black.
    # --------------------------------------------------------

    pixels(
        draw,
        x,
        y,
        pattern,
        fill="black"
    )


# ============================================================
# DRAW HOME SCREEN
# ============================================================

def draw_screen():

    now = datetime.now()

    time_text = now.strftime("%H:%M")

    date_text = (
        f"{weekdays[now.weekday()]} "
        f"{now.day} "
        f"{months[now.month - 1]}"
    )

    with canvas(device) as draw:

        # ----------------------------------------------------
        # CONNECTION
        # ----------------------------------------------------

        draw_icon(
            draw,
            ICONS[0],
            selected == 0
        )


        # ----------------------------------------------------
        # CLOCK
        # ----------------------------------------------------

        bbox = draw.textbbox(
            (0, 0),
            time_text,
            font=font_time
        )

        time_width = bbox[2] - bbox[0]

        draw.text(
            (
                (128 - time_width) // 2,
                18
            ),
            time_text,
            font=font_time,
            fill="white"
        )


        # ----------------------------------------------------
        # DATE
        # ----------------------------------------------------

        bbox = draw.textbbox(
            (0, 0),
            date_text,
            font=font_date
        )

        date_width = bbox[2] - bbox[0]

        draw.text(
            (
                (128 - date_width) // 2,
                40
            ),
            date_text,
            font=font_date,
            fill="white"
        )


        # ----------------------------------------------------
        # PLUS
        # ----------------------------------------------------

        draw_icon(
            draw,
            ICONS[2],
            selected == 2
        )


        # ----------------------------------------------------
        # SETTINGS
        # ----------------------------------------------------

        draw_icon(
            draw,
            ICONS[1],
            selected == 1
        )


# ============================================================
# ENCODER UPDATE
# ============================================================

def update_encoder():

    global selected
    global last_encoder_position

    position = encoder.steps

    if position > last_encoder_position:

        selected = (selected + 1) % len(ICONS)

        last_encoder_position = position

        draw_screen()

    elif position < last_encoder_position:

        selected = (selected - 1) % len(ICONS)

        last_encoder_position = position

        draw_screen()


# ============================================================
# BUTTON
# ============================================================

def button_pressed():

    icon = ICONS[selected]

    print(
        "Selected:",
        icon["name"]
    )


button.when_pressed = button_pressed


# ============================================================
# INITIAL DRAW
# ============================================================

draw_screen()


# ============================================================
# MAIN LOOP
#
# Two things happen independently:
#
#   - encoder is checked continuously
#   - clock is refreshed every second
#
# ============================================================

last_second = None

try:

    while True:

        # --------------------------------------------
        # Encoder
        # --------------------------------------------

        update_encoder()


        # --------------------------------------------
        # Clock
        #
        # Redraw only when the second changes.
        # --------------------------------------------

        now = datetime.now()

        if now.second != last_second:

            last_second = now.second

            draw_screen()


        sleep(0.01)


except KeyboardInterrupt:

    print("\nExiting...")

    device.clear()
