from pathlib import Path

from pico2d import *

class Grass:
    def __init__(self):
        image_path = Path(__file__).resolve().parent / 'grass.png'
        self.image = load_image(str(image_path))

    def draw(self):
        self.image.draw(400, 30)

    def update(self):
        pass
