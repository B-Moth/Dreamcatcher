from PIL import Image


class Animation:
    def __init__(self, filename, frame_width=128, frame_height=64, fps=8):
        self.image = Image.open(filename).convert("1")

        self.frame_width = frame_width
        self.frame_height = frame_height
        self.fps = fps

        self.frame_count = self.image.width // frame_width

        self.current_frame = 0
        self.elapsed = 0.0

    def update(self, dt):
        self.elapsed += dt

        frame_duration = 1.0 / self.fps

        while self.elapsed >= frame_duration:
            self.elapsed -= frame_duration

            self.current_frame += 1

            if self.current_frame >= self.frame_count:
                self.current_frame = 0

    def get_frame(self):
        x = self.current_frame * self.frame_width

        return self.image.crop(
            (
                x,
                0,
                x + self.frame_width,
                self.frame_height
            )
        )

    def draw(self, draw, x=0, y=0):
        frame = self.get_frame()

        draw.bitmap(
            (x, y),
            frame,
            fill="white"
        )
