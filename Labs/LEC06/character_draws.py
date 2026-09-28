# 실습 과제 진행

from pico2d import *
import math

open_canvas()


character = load_image('character.png')

# 삼각형 꼭짓점
A = (100, 100)
B = (700, 100)
C = (400, 500)

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
    
  

def interpolate(x0, y0, x1, y1, t):
    # 두 점을 잇는 선분 위에서 t만큼 진행한 좌표를 계산한다.
    x = x0 + (x1 - x0) * t
    y = y0 + (y1 - y0) * t
    return x, y


def move_triangle():
    print('triangle')
    

while True:
    # move_circle()
    move_rectangle()
    move_triangle()

   