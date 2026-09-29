"""
스프라이트 시트 생성기
=====================
4종 애니메이션(걷기 / 뛰기 / 점프 / 공격)을 개별 PNG 시트로 생성한다.

- animation_viewer.py 가 불러올 PNG 와 JSON 메타데이터를 만든다.
- 프레임마다 크기가 다른 "복잡한 스프라이트 시트" 형태를 만들기 위해
  각 프레임을 개별 크기(가변 높이/너비)로 렌더링한다.
- Pillow 를 사용해 실행한다:  python make_sprite_sheet.py
"""

import json
import math
import os

from PIL import Image, ImageDraw

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# 애니메이션 정의: 이름 -> 프레임 포즈 리스트
# 포즈는 (관절 각도, 몸체 y 오프셋, 팔 각도) 튜플로 표현한다.
ANIMATIONS = {
    "walk": {
        "fps": 8,
        "poses": [
            (0, 0, 18), (0, -2, 9), (0, 0, 0), (0, -2, -9),
            (0, 0, -18), (0, -2, -9), (0, 0, 0), (0, -2, 9),
        ],
    },
    "run": {
        "fps": 12,
        "poses": [
            (22, 0, 34), (18, -6, 22), (10, -3, 8), (4, -8, -6),
            (0, -4, -18), (4, 0, -28), (10, -6, -22), (18, -3, -8),
        ],
    },
    "jump": {
        "fps": 6,
        "poses": [
            (0, 14, -26), (4, 26, -18), (0, 4, 6),
            (-6, -30, 20), (0, -12, 12), (0, 0, 0), (0, 8, -10),
        ],
    },
    "attack": {
        "fps": 10,
        "poses": [
            (0, 0, -50), (0, -3, -64), (6, -6, -30), (14, -4, 20),
            (20, 0, 52), (12, 3, 70), (4, 0, 40),
        ],
    },
}

# 팔레트 (RGBA)
SKIN = (247, 214, 174, 255)
OUTLINE = (38, 40, 48, 255)
SHIRT = (72, 141, 214, 255)
SHIRT_DARK = (52, 106, 172, 255)
PANTS = (48, 54, 74, 255)
SHOE = (30, 32, 40, 255)
EYE = (28, 30, 38, 255)
BLADE = (214, 226, 240, 255)
BLADE_EDGE = (150, 168, 190, 255)

# 캐릭터 기본 기하 (논리 좌표계, y 는 위쪽이 양수)
HEAD_R = 15
HEAD_CY = 66
SHOULDER_W = 11
HIP_W = 8
TORSO_TOP = 50
TORSO_BOTTOM = 20
UPPER_ARM = 17
FORE_ARM = 16
THIGH = 18
SHIN = 18
FOOT = 12

BASE_W = 96
BASE_H = 110


def _rot(x, y, deg):
    rad = math.radians(deg)
    c, s = math.cos(rad), math.sin(rad)
    return x * c - y * s, x * s + y * c


def _limb(draw, x0, y0, angle, length, width, color):
    """각도(angle) 만큼 기울어진 팔다리를 두 마디로 그린다."""
    mid = (x0 + _rot(0, -length * 0.55, angle)[0],
           y0 + _rot(0, -length * 0.55, angle)[1])
    end = (mid[0] + _rot(0, -length * 0.45, angle * 0.35)[0],
           mid[1] + _rot(0, -length * 0.45, angle * 0.35)[1])
    for a, b in (((x0, y0), mid), (mid, end)):
        draw.line([a, b], fill=OUTLINE, width=width + 4, joint="curve")
    for a, b in (((x0, y0), mid), (mid, end)):
        draw.line([a, b], fill=color, width=width, joint="curve")
    return mid, end
