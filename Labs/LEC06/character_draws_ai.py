# AI로 작성한 LEC06 실습 과제 완성본
#
# 요구사항
#   1. 캐릭터가 원 경로를 한 바퀴 이동한다.
#   2. 캐릭터가 사각형 경로를 한 바퀴 이동한다.
#   3. 캐릭터가 삼각형 경로를 한 바퀴 이동한다.
#   4. 위 세 운동을 원 -> 사각 -> 삼각 순서로 무한 반복한다.

from pico2d import *
import math
import os

# --- 공통 설정 ---
CANVAS_W = 800
CANVAS_H = 600
FRAME_DELAY = 0.01

# --- 원운동 경로 ---
FULL_TURN = 360
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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
character = load_image(os.path.join(SCRIPT_DIR, 'character.png'))


def draw_character(x: float, y: float) -> None:
    """계산한 좌표에 캐릭터를 그리고 화면을 갱신한다."""
    clear_canvas()
    character.draw(x, y)
    update_canvas()
    delay(FRAME_DELAY)


def interpolate(x0: float, y0: float,
                x1: float, y1: float, t: float) -> tuple:
    """두 점을 잇는 선분 위에서 진행 비율 t 만큼 이동한 좌표."""
    return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t


def move_circle() -> None:
    """원 경로를 한 바퀴 이동한다."""
    for degree in range(FULL_TURN):
        theta = math.radians(degree)
        x = CENTER_X + RADIUS * math.cos(theta)
        y = CENTER_Y + RADIUS * math.sin(theta)
        draw_character(x, y)


def move_top() -> None:
    """사각형 상단 변을 오른쪽으로 이동한다."""
    for x in range(MARGIN, CANVAS_W - MARGIN + 1, EDGE_STEP):
        draw_character(x, CANVAS_H - MARGIN)


def move_right() -> None:
    """사각형 오른쪽 변을 위로 이동한다."""
    for y in range(CANVAS_H - MARGIN, MARGIN - 1, -EDGE_STEP):
        draw_character(CANVAS_W - MARGIN, y)


def move_bottom() -> None:
    """사각형 하단 변을 왼쪽으로 이동한다."""
    for x in range(CANVAS_W - MARGIN, MARGIN - 1, -EDGE_STEP):
        draw_character(x, MARGIN)


def move_left() -> None:
    """사각형 왼쪽 변을 아래로 이동한다."""
    for y in range(MARGIN, CANVAS_H - MARGIN + 1, EDGE_STEP):
        draw_character(MARGIN, y)


def move_rectangle() -> None:
    """사각형 네 변을 시계 방향으로 연결한다."""
    move_top()
    move_right()
    move_bottom()
    move_left()


def move_segment(x0: float, y0: float, x1: float, y1: float) -> None:
    """두 점 사이를 등간격으로 이동한다."""
    for step in range(TRIANGLE_SEGMENTS + 1):
        t = step / TRIANGLE_SEGMENTS
        x, y = interpolate(x0, y0, x1, y1, t)
        draw_character(x, y)


def move_triangle() -> None:
    """삼각형 세 변을 연결한다."""
    points = [TRIANGLE_A, TRIANGLE_B, TRIANGLE_C]
    for i in range(len(points)):
        start = points[i]
        end = points[(i + 1) % len(points)]
        move_segment(start[0], start[1], end[0], end[1])


def main() -> None:
    """원, 사각, 삼각 운동을 순서대로 무한 반복한다."""
    while True:
        move_circle()
        move_rectangle()
        move_triangle()


if __name__ == '__main__':
    main()
