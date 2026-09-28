from pico2d import *
import math

open_canvas(800, 600)

character = load_image('character.png')


def draw_character(x, y):
    clear_canvas()
    character.draw(x, y)
    update_canvas()
    delay(0.01)


def move_circle():
    pass


def move_rectangle():
    pass


def move_triangle():
    pass


while True:
    pass
