from pathlib import Path

from pico2d import load_image
from transitions import Machine


class Boy:
    def __init__(self):
        self.x, self.y = 400, 90
        self.frame = 0
        self.face_dir = 1
        image_path = Path(__file__).resolve().parent / 'animation_sheet.png'
        self.image = load_image(str(image_path))
        self.machine = Machine(
            model=self,
            states=['IDLE'],
            initial='IDLE',
            auto_transitions=False,
        )

    def update(self):
        if self.state == 'IDLE':
            self.frame = (self.frame + 1) % 8

    def draw(self):
        if self.state == 'IDLE':
            source_y = 300 if self.face_dir == 1 else 200
            self.image.clip_draw(self.frame * 100, source_y, 100, 100, self.x, self.y)