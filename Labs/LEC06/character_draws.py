# 실습 과제 진행

from pico2d import *
import math

open_canvas()


character = load_image('character.png')

def move_circle():
    for degree in range(360):
        theta = math.radians(degree)
        x = 400 + 200 * math.cos(theta)
        y = 300 + 200 * math.sin(theta)

        clear_canvas()
        character.draw(x, y)
        update_canvas()
        delay(0.01)
    pass


def draw_top():
    print('Top')
    pass
def draw_bottom():
    print('Bottom')
    pass
def draw_left():
    print('Left')
    pass
def draw_right():
    print('Right')
    pass




def move_rectangle():
    print('rectangle')
    draw_top()
    draw_bottom()
    draw_left()
    draw_right()
    pass

def move_triangle():
    print('triangle')
    pass

while True:
    move_circle()
    move_rectangle()
    move_triangle()

    pass
