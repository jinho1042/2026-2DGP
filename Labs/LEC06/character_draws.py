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
    


def draw_right():
    for x in range(50, 750,5):
        clear_canvas()
        character.draw(x, 550)
        update_canvas()
        delay(0.01)

def draw_left():
    for x in range(750, 50, -5):
        clear_canvas()
        character.draw(x, 50)
        update_canvas()
        delay(0.01)

def draw_top():
    for y in range(50, 550, 5):
        clear_canvas()
        character.draw(50, y)
        update_canvas()
        delay(0.01)

def draw_bottom():
    for y in range(550, 50, -5):
        clear_canvas()  
        character.draw(750, y)
        update_canvas()
        delay(0.01)

    

def move_rectangle():
    print('rectangle')
    draw_top()
    draw_right()
    draw_bottom()
    draw_left()
    
  

def move_triangle():
    print('triangle')
    

while True:
    # move_circle()
    move_rectangle()
    move_triangle()

   