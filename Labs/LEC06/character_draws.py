# 실습 과제 진행

from pico2d import *
import math

open_canvas()


character = load_image('character.png')

# 삼각형 한 변을 나누는 구간 수
SEGMENTS = 40

# 삼각형 꼭짓점
A = (100, 100)
B = (700, 100)
C = (400, 500)

def draw_character(x, y):
    # 좌표 계산과 화면 출력을 분리한 공통 그리기 함수
    clear_canvas()
    character.draw(x, y)
    update_canvas()
    delay(0.01)


def move_circle():
    for degree in range(360):
        theta = math.radians(degree)
        x = 400 + 200 * math.cos(theta)
        y = 300 + 200 * math.sin(theta)

        draw_character(x, y)


def draw_right():
    for x in range(50, 750,5):
        draw_character(x, 550)

def draw_left():
    for x in range(750, 50, -5):
        draw_character(x, 50)

def draw_top():
    for y in range(50, 550, 5):
        draw_character(50, y)

def draw_bottom():
    for y in range(550, 50, -5):
        draw_character(750, y)

    

def move_rectangle():
    draw_top()
    draw_right()
    draw_bottom()
    draw_left()
    
  

def interpolate(x0, y0, x1, y1, t):
    # 두 점을 잇는 선분 위에서 t만큼 진행한 좌표를 계산한다.
    x = x0 + (x1 - x0) * t
    y = y0 + (y1 - y0) * t
    return x, y


def move_ab():
    for step in range(SEGMENTS + 1):
        t = step / SEGMENTS
        x, y = interpolate(A[0], A[1], B[0], B[1], t)

        clear_canvas()
        character.draw(x, y)
        update_canvas()
        delay(0.01)


def move_bc():
    for step in range(SEGMENTS + 1):
        t = step / SEGMENTS
        x, y = interpolate(B[0], B[1], C[0], C[1], t)

        clear_canvas()
        character.draw(x, y)
        update_canvas()
        delay(0.01)


def move_ca():
    for step in range(SEGMENTS + 1):
        t = step / SEGMENTS
        x, y = interpolate(C[0], C[1], A[0], A[1], t)

        clear_canvas()
        character.draw(x, y)
        update_canvas()
        delay(0.01)


def move_triangle():
    move_ab()
    move_bc()
    move_ca()


while True:
    move_circle()
    move_rectangle()
    move_triangle()

   