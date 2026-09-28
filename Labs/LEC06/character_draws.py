# 실습 과제 진행

from pico2d import *
import math

# --- 공통 설정 ---
FRAME_DELAY = 0.01

# --- 캔버스 크기 ---
CANVAS_W = 800
CANVAS_H = 600

# --- 원운동 경로 ---
CENTER_X = 400
CENTER_Y = 300
RADIUS = 200

# --- 사각형 경로 ---
MARGIN = 50
EDGE_STEP = 5

# --- 삼각형 경로 ---
TRIANGLE_SEGMENTS = 40
TRIANGLE_A = (100, 100)
TRIANGLE_B = (700, 100)
TRIANGLE_C = (400, 500)

open_canvas(CANVAS_W, CANVAS_H)


character = load_image('character.png')


def draw_character(x, y):
    # 좌표 계산과 화면 출력을 분리한 공통 그리기 함수
    clear_canvas()
    character.draw(x, y)
    update_canvas()
    delay(FRAME_DELAY)


def move_circle():
    for degree in range(360):
        theta = math.radians(degree)
        x = CENTER_X + RADIUS * math.cos(theta)
        y = CENTER_Y + RADIUS * math.sin(theta)

        draw_character(x, y)


def move_top():
    for x in range(MARGIN, CANVAS_W - MARGIN + 1, EDGE_STEP):
        draw_character(x, CANVAS_H - MARGIN)


def move_right():
    for y in range(CANVAS_H - MARGIN, MARGIN - 1, -EDGE_STEP):
        draw_character(CANVAS_W - MARGIN, y)


def move_bottom():
    for x in range(CANVAS_W - MARGIN, MARGIN - 1, -EDGE_STEP):
        draw_character(x, MARGIN)


def move_left():
    for y in range(MARGIN, CANVAS_H - MARGIN + 1, EDGE_STEP):
        draw_character(MARGIN, y)


def move_rectangle():
    move_top()
    move_right()
    move_bottom()
    move_left()
    
  

def interpolate(x0, y0, x1, y1, t):
    # 두 점을 잇는 선분 위에서 t만큼 진행한 좌표를 계산한다.
    x = x0 + (x1 - x0) * t
    y = y0 + (y1 - y0) * t
    return x, y


def move_segment(x0, y0, x1, y1):
    # 두 점을 잇는 선분을 TRIANGLE_SEGMENTS 등분해서 이동한다.
    for step in range(TRIANGLE_SEGMENTS + 1):
        t = step / TRIANGLE_SEGMENTS
        x, y = interpolate(x0, y0, x1, y1, t)
        draw_character(x, y)


def move_ab():
    move_segment(TRIANGLE_A[0], TRIANGLE_A[1], TRIANGLE_B[0], TRIANGLE_B[1])


def move_bc():
    move_segment(TRIANGLE_B[0], TRIANGLE_B[1], TRIANGLE_C[0], TRIANGLE_C[1])


def move_ca():
    move_segment(TRIANGLE_C[0], TRIANGLE_C[1], TRIANGLE_A[0], TRIANGLE_A[1])


def move_triangle():
    move_ab()
    move_bc()
    move_ca()


while True:
    move_circle()
    move_rectangle()
    move_triangle()

   