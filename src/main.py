from time import sleep
from pathlib import Path
import select
import socket
import subprocess
import sys

fps = 10
# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ANIMATION_DIR = BASE_DIR / "assets" / "animations"
CONTROL_SOCKET = Path("/tmp/dreamcatcher.sock")


def send_command(command):

    try:

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:

            client.settimeout(2)
            client.connect(str(CONTROL_SOCKET))
            client.sendall(f"{command}\n".encode())

            response = client.recv(1024).decode().strip()

            if response:
                print(response)

    except (ConnectionRefusedError, FileNotFoundError, TimeoutError):

        print(
            "Dreamcatcher is not running or the control socket is unavailable.",
            file=sys.stderr
        )

        return 1

    return 0


if len(sys.argv) > 1:

    if len(sys.argv) != 3 or sys.argv[1] != "icon":

        print(
            "Usage: python3 src/main.py icon {next|prev|select}",
            file=sys.stderr
        )

        sys.exit(2)

    sys.exit(
        send_command(
            f"{sys.argv[1]} {sys.argv[2]}"
        )
    )


from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306

from PIL import ImageFont

from gpiozero import RotaryEncoder, Button

from clock import get_time
from animation import Animation


# ============================================================
# OLED
# ============================================================

serial = i2c(
    port=1,
    address=0x3C
)

device = ssd1306(
    serial,
    width=128,
    height=64
)


# ============================================================
# FONT
# ============================================================

font_clock = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    9
)


# ============================================================
# ANIMATIONS
# ============================================================

animation_files = sorted(
    ANIMATION_DIR.glob("*.png")
)

if not animation_files:
    raise RuntimeError(
        f"No animations found in {ANIMATION_DIR}"
    )


animation_index = 1

animation = Animation(
    str(animation_files[animation_index]),
    fps
)


def load_animation(index):

    global animation
    global animation_index

    animation_index = index % len(animation_files)

    filename = animation_files[animation_index]

    print(
        f"Animation: {filename.name}"
    )

    animation = Animation(
        str(filename),
        fps
    )


# ============================================================
# EC11
# ============================================================

ENCODER_A = 17
ENCODER_B = 18
ENCODER_BUTTON = 22


encoder = RotaryEncoder(
    a=ENCODER_A,
    b=ENCODER_B,
    max_steps=0
)

button = Button(
    ENCODER_BUTTON
)


# ============================================================
# MENU
# ============================================================

# 0 = Wi-Fi
# 1 = settings
# 2 = new entry
# 3 = animation

selected = 0

MENU_COUNT = 4
ICON_NAMES = [
    "wifi",
    "settings",
    "new entry",
    "animation"
]


def encoder_changed():

    global selected

    if encoder.steps > 0:

        selected = (
            selected + 1
        ) % MENU_COUNT

        encoder.steps = 0

    elif encoder.steps < 0:

        selected = (
            selected - 1
        ) % MENU_COUNT

        encoder.steps = 0


encoder.when_rotated = encoder_changed


# ============================================================
# BUTTON
# ============================================================

def select_icon():

    if selected == 3:

        next_animation = (
            animation_index + 1
        ) % len(animation_files)

        load_animation(
            next_animation
        )

    else:

        print(
            f"Selected icon: {ICON_NAMES[selected]}"
        )


def button_pressed():

    select_icon()


button.when_pressed = button_pressed


def handle_command(command):

    global selected

    if command == "icon next":

        selected = (
            selected + 1
        ) % MENU_COUNT

    elif command == "icon prev":

        selected = (
            selected - 1
        ) % MENU_COUNT

    elif command == "icon select":

        select_icon()

    else:

        return "Unknown command. Use: icon {next|prev|select}"

    return (
        f"Icon: {ICON_NAMES[selected]}"
    )


def create_control_socket():

    if CONTROL_SOCKET.exists():
        CONTROL_SOCKET.unlink()

    control_socket = socket.socket(
        socket.AF_UNIX,
        socket.SOCK_STREAM
    )

    control_socket.bind(str(CONTROL_SOCKET))
    CONTROL_SOCKET.chmod(0o666)
    control_socket.listen()
    control_socket.setblocking(False)

    return control_socket


def poll_commands(control_socket):

    readable = [control_socket]

    if sys.stdin.isatty():
        readable.append(sys.stdin)

    ready, _, _ = select.select(
        readable,
        [],
        [],
        0
    )

    if sys.stdin in ready:

        command = sys.stdin.readline().strip()

        if command:
            print(handle_command(command))

    if control_socket in ready:

        while True:

            try:
                client, _ = control_socket.accept()

            except BlockingIOError:
                break

            with client:

                command = client.recv(1024).decode().strip()
                client.sendall(
                    f"{handle_command(command)}\n".encode()
                )


# ============================================================
# PIXEL ART
# ============================================================

def pixels(draw, x, y, pattern):

    for py, row in enumerate(pattern):

        for px, pixel in enumerate(row):

            if pixel == "#":

                draw.point(
                    (
                        x + px,
                        y + py
                    ),
                    fill="white"
                )


# ============================================================
# WIFI
# ============================================================

def wifi_connected():

    try:

        result = subprocess.run(
            [
                "iwgetid",
                "-r"
            ],
            capture_output=True,
            text=True,
            timeout=2
        )

        return bool(
            result.stdout.strip()
        )

    except (
        subprocess.SubprocessError,
        FileNotFoundError
    ):

        return False


# ============================================================
# CONNECTION ICON
# ============================================================

def draw_connection(
    draw,
    x,
    y,
    connected
):

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
            ".#...##...#."
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
# ANIMATION ICON
# ============================================================

def draw_animation_icon(draw, x, y):

    pattern = [
        ".....#####......",
        "...##.....##....",
        "..#.........#...",
        ".#...........#..",
        ".#...........#..",
        "###############.",
        "#.##..####..#.#.",
        "#.###.#.###.#.#.",
	"#..###...###..#.",
	"#.............#.",
	".#..#........#..",
	".#...####....#..",
	"..#.........#...",
	"...##.....##....",
	".....#####......"

    ]

    pixels(
        draw,
        x,
        y,
        pattern
    )


# ============================================================
# SELECTED ICON
# ============================================================

def draw_selected_icon(draw):

    center_x = 115
    center_y = 24

    # --------------------------------------------------------
    # Wi-Fi
    # --------------------------------------------------------

    if selected == 0:

        connected = wifi_connected()

        x = center_x - 4
        y = center_y - 5

        draw_connection(
            draw,
            x,
            y,
            connected
        )

    # --------------------------------------------------------
    # Settings
    # --------------------------------------------------------

    elif selected == 1:

        x = center_x - 7
        y = center_y - 7

        draw_gear(
            draw,
            x,
            y
        )

    # --------------------------------------------------------
    # New entry
    # --------------------------------------------------------

    elif selected == 2:

        x = center_x - 9
        y = center_y - 5

        draw_plus(
            draw,
            x,
            y
        )

    # --------------------------------------------------------
    # Animation
    # --------------------------------------------------------

    elif selected == 3:

        x = center_x - 8
        y = center_y - 4

        draw_animation_icon(
            draw,
            x,
            y
        )


# ============================================================
# CLOCK
# ============================================================

def draw_clock(draw):

    time_text = get_time()

    bbox = draw.textbbox(
        (0, 0),
        time_text,
        font=font_clock
    )

    width = bbox[2] - bbox[0]

    x = 128 - width - 3
    y = 1

    draw.text(
        (x, y),
        time_text,
        font=font_clock,
        fill="white"
    )


# ============================================================
# MAIN LOOP
# ============================================================

control_socket = create_control_socket()

try:

    while True:

        poll_commands(control_socket)

        frame = animation.get_frame()

        with canvas(device) as draw:

            # ------------------------------------------------
            # BACKGROUND ANIMATION
            # ------------------------------------------------

            draw.bitmap(
                (0, 0),
                frame,
                fill="white"
            )

            # ------------------------------------------------
            # CLOCK
            # ------------------------------------------------

            draw_clock(draw)

            # ------------------------------------------------
            # MENU ICON
            # ------------------------------------------------

            draw_selected_icon(draw)

        animation.next_frame()

        sleep(
            animation.frame_delay()
        )


except KeyboardInterrupt:

    device.clear()

finally:

    control_socket.close()

    if CONTROL_SOCKET.exists():
        CONTROL_SOCKET.unlink()
