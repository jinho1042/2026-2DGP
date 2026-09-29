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


def _draw_leg(draw, hip, angle, leg_len_scale=1.0, front=True):
    """다리: 허벅지 + 정강이 + 신발."""
    color = PANTS
    thigh_len = THIGH * leg_len_scale
    shin_len = SHIN * leg_len_scale
    knee, foot = _limb(draw, hip[0], hip[1], angle, thigh_len + shin_len, 8, color)
    # 신발
    fx = foot[0]
    fy = foot[1]
    heel = (fx - _rot(FOOT * 0.4, 0, angle)[0], fy - _rot(FOOT * 0.4, 0, angle)[1])
    toe = (fx + _rot(FOOT * 0.6, 0, angle)[0], fy + _rot(FOOT * 0.6, 0, angle)[1])
    draw.line([heel, toe], fill=OUTLINE, width=13, joint="curve")
    draw.line([heel, toe], fill=SHOE, width=9, joint="curve")
    return knee, foot


def _draw_arm(draw, shoulder, angle, arm_len_scale=1.0):
    """팔: 위팔 + forearm + 손."""
    upper = UPPER_ARM * arm_len_scale
    fore = FORE_ARM * arm_len_scale
    elbow, hand = _limb(draw, shoulder[0], shoulder[1], angle, upper + fore, 7, SKIN)
    r = 5
    draw.ellipse([hand[0] - r - 2, hand[1] - r - 2,
                  hand[0] + r + 2, hand[1] + r + 2], fill=OUTLINE)
    draw.ellipse([hand[0] - r, hand[1] - r, hand[0] + r, hand[1] + r], fill=SKIN)
    return elbow, hand


def _draw_torso(draw, lean, y_off):
    """몸통: 셔츠 + 어깨/골반 라인."""
    top_y = TORSO_TOP + y_off
    bot_y = TORSO_BOTTOM + y_off
    tl = (lean * 0.5, top_y)
    tr = (lean * 0.5 + SHOULDER_W * 2, top_y + lean * 0.15)
    bl = (0, bot_y)
    br = (HIP_W * 2, bot_y + lean * 0.05)
    draw.polygon([(tl[0] - 4, tl[1] - 2), (tr[0] + 4, tr[1] - 2),
                  (br[0] + 3, br[1] + 2), (bl[0] - 3, bl[1] + 2)],
                 fill=OUTLINE)
    draw.polygon([tl, (tr[0] - 1, tr[1] + 1), (br[0] - 1, br[1] - 1), bl],
                 fill=SHIRT)
    # 셔츠 하이라이트/그늘
    draw.polygon([(tl[0] + 3, tl[1] + 3), (tr[0] - 5, tr[1] + 3),
                  (br[0] - 4, br[1] - 2), (bl[0] + 2, bl[1] - 2)],
                 fill=SHIRT_DARK)
    return (lean * 0.5 + SHOULDER_W, top_y + 1), (HIP_W, bot_y)


def _draw_head(draw, cx, cy, lean):
    """머리: 원 + 눈 + 머리카락."""
    r = HEAD_R
    draw.ellipse([cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3], fill=OUTLINE)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=SKIN)
    # 머리카락 (윗부분)
    draw.chord([cx - r - 1, cy - r - 3, cx + r + 1, cy + r * 0.4],
               180, 360, fill=(74, 58, 48, 255))
    # 눈
    ey = cy + 2
    ex_off = lean * 0.25
    draw.ellipse([cx - 6 + ex_off, ey - 3, cx - 1 + ex_off, ey + 3], fill=EYE)
    draw.ellipse([cx + 2 + ex_off, ey - 3, cx + 7 + ex_off, ey + 3], fill=EYE)
    # 눈 하이라이트
    draw.ellipse([cx - 5 + ex_off, ey - 2, cx - 4 + ex_off, ey], fill=(255, 255, 255, 255))
    draw.ellipse([cx + 3 + ex_off, ey - 2, cx + 4 + ex_off, ey], fill=(255, 255, 255, 255))


def _draw_sword(draw, hand, angle):
    """검: 손 위치에서 각도 방향으로 뻗는 날."""
    dx, dy = _rot(0, -1, angle)
    length = 34
    tipx = hand[0] + dx * length
    tipy = hand[1] + dy * length
    # 손잡이
    gx = hand[0] - dx * 6
    gy = hand[1] - dy * 6
    draw.line([(hand[0], hand[1]), (gx, gy)], fill=(96, 70, 48, 255), width=5)
    # 검신(너비 있는 폴리곤)
    px, py = -dy, dx
    draw.polygon([(gx + px * 4, gy + py * 4), (tipx + px * 1.5, tipy + py * 1.5),
                  (tipx - px * 1.5, tipy - py * 1.5), (gx - px * 4, gy - py * 4)],
                 fill=BLADE_EDGE)
    draw.polygon([(gx + px * 2.5, gy + py * 2.5), (tipx + px * 0.8, tipy + py * 0.8),
                  (tipx - px * 0.8, tipy - py * 0.8), (gx - px * 2.5, gy - py * 2.5)],
                 fill=BLADE)
