from PIL import Image


class Animation:

    def __init__(self, filename, fps=7, frame_width=128, frame_height=64):

        self.image = Image.open(filename).convert("1")

        self.frame_width = frame_width
        self.frame_height = frame_height

        if self.image.width < self.frame_width or self.image.height < self.frame_height:
            raise ValueError(
                f"Image too small for animation: {self.image.size} "
                f"< ({self.frame_width}, {self.frame_height})"
            )

        self.frame_count = self.image.width // self.frame_width

        if self.frame_count <= 0:
            raise ValueError(
                f"No complete animation frames found in {filename}: "
                f"width={self.image.width}, frame_width={self.frame_width}"
            )

        self.fps = fps
        self.current_frame = 0

    def get_frame(self):

        x = self.current_frame * self.frame_width

        frame = self.image.crop(
            (
                x,
                0,
                x + self.frame_width,
                self.frame_height
            )
        )

        return frame.copy()

    def next_frame(self):

        self.current_frame = (self.current_frame + 1) % self.frame_count

    def frame_delay(self):

        return 1 / self.fps
