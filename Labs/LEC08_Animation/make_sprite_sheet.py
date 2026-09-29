"""
스프라이트 시트 생성기
=====================
4종 애니메이션(걷기 / 뛰기 / 점프 / 공격)을 PNG 시트로 생성한다.

- animation_viewer.py 가 불러올 PNG 와 JSON 메타데이터를 만든다.
- 프레임마다 크기가 다른 "복잡한 스프라이트 시트"를 만들기 위해
  각 프레임을 개별 캔버스에 렌더링 후 가변 크기로 시트에 배치한다.
- 실행:  python make_sprite_sheet.py

모든 드로잉은 픽셀 좌표(왼쪽 위 기준) 또는 논리 좌표(발 기준, y 위쪽이 +) 를
명시적으로 변환해 사용한다.
"""

import json
import math
import os

from PIL import Image, ImageDraw

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------
# 애니메이션 정의
# pose = (관절 각도, 몸체 y 오프셋, 앞팔 각도)
# ---------------------------------------------------------------
ANIMATIONS = [
    {
        "name": "walk",
        "fps": 8,
        "poses": [
            (0, 0, 18), (0, -2, 9), (0, 0, 0), (0, -2, -9),
            (0, 0, -18), (0, -2, -9), (0, 0, 0), (0, -2, 9),
        ],
    },
    {
        "name": "run",
        "fps": 14,
        "poses": [
            (24, 0, 36), (20, -7, 24), (12, -4, 8), (5, -9, -8),
            (0, -5, -20), (5, 0, -30), (12, -7, -24), (20, -4, -8),
        ],
    },
    {
        "name": "jump",
        "fps": 6,
        "poses": [
            (0, 16, -28), (6, 30, -20), (2, 6, 6),
            (-8, -34, 22), (0, -14, 12), (0, 0, 0), (0, 10, -12),
        ],
    },
    {
        "name": "attack",
        "fps": 11,
        "poses": [
            (0, 0, -52), (0, -4, -66), (8, -7, -32), (16, -5, 20),
            (22, 0, 54), (14, 4, 72), (5, 0, 42),
        ],
    },
]

# ---------------------------------------------------------------
# 팔레트
# ---------------------------------------------------------------
SKIN = (247, 214, 174, 255)
HAIR = (74, 58, 48, 255)
OUTLINE = (38, 40, 48, 255)
SHIRT = (72, 141, 214, 255)
SHIRT_DARK = (52, 106, 172, 255)
PANTS = (48, 54, 74, 255)
PANTS_DARK = (36, 41, 56, 255)
SHOE = (30, 32, 40, 255)
EYE = (28, 30, 38, 255)
BLADE = (214, 226, 240, 255)
BLADE_EDGE = (150, 168, 190, 255)
HILT = (96, 70, 48, 255)

# ---------------------------------------------------------------
# 캐릭터 기하 (논리 좌표: 발밑이 y=0, 위쪽이 +y)
# ---------------------------------------------------------------
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

# 프레임 논리 크기 (발밑 중앙 기준)
FRAME_W = 110
FRAME_H = 120
GROUND_Y = 6  # 발밑 여백

# 슈퍼샘플링 배율
SS = 4


def rot(x, y, deg):
    rad = math.radians(deg)
    c, s = math.cos(rad), math.sin(rad)
    return x * c - y * s, x * s + y * c


# ---------------------------------------------------------------
# 파츠 드로잉 (모두 논리 좌표, y 위쪽이 +)
# ---------------------------------------------------------------
def draw_leg(d, hip, angle, dark=False):
    """다리: 허벅지 + 정강이 + 신발. knee, foot 반환."""
    color = PANTS_DARK if dark else PANTS
    ox, oy = hip
    mx, my = ox + rot(0, -(THIGH), angle)[0], oy + rot(0, -(THIGH), angle)[1]
    fx, fy = mx + rot(0, -(SHIN), angle * 0.3)[0], my + rot(0, -(SHIN), angle * 0.3)[1]

    for a, b in (((ox, oy), (mx, my)), ((mx, my), (fx, fy))):
        d.line([a, b], fill=OUTLINE, width=13, joint="curve")
    for a, b in (((ox, oy), (mx, my)), ((mx, my), (fx, fy))):
        d.line([a, b], fill=color, width=8, joint="curve")
    # 무릎
    d.ellipse([mx - 5, my - 5, mx + 5, my + 5], fill=color)

    # 신발: 발목에서 앞쪽으로
    tx, ty = rot(FOOT * 0.6, -2, angle)
    heelx, heely = rot(-FOOT * 0.4, -2, angle)
    d.line([(fx + heelx, fy + heely), (fx + tx, fy + ty)],
           fill=OUTLINE, width=14, joint="curve")
    d.line([(fx + heelx, fy + heely), (fx + tx, fy + ty)],
           fill=SHOE, width=10, joint="curve")
    return (mx, my), (fx, fy)


def draw_arm(d, shoulder, angle, dark=False):
    """팔: 위팔 + 전완 + 손. elbow, hand 반환."""
    ox, oy = shoulder
    ex, ey = ox + rot(0, -(UPPER_ARM), angle)[0], oy + rot(0, -(UPPER_ARM), angle)[1]
    hx, hy = ex + rot(0, -(FORE_ARM), angle * 0.4)[0], ey + rot(0, -(FORE_ARM), angle * 0.4)[1]
    color = (208, 176, 140, 255) if dark else SKIN
    for a, b in (((ox, oy), (ex, ey)), ((ex, ey), (hx, hy))):
        d.line([a, b], fill=OUTLINE, width=11, joint="curve")
    for a, b in (((ox, oy), (ex, ey)), ((ex, ey), (hx, hy))):
        d.line([a, b], fill=color, width=7, joint="curve")
    d.ellipse([hx - 6, hy - 6, hx + 6, hy + 6], fill=OUTLINE)
    d.ellipse([hx - 4, hy - 4, hx + 4, hy + 4], fill=color)
    return (ex, ey), (hx, hy)


def draw_torso(d, lean, y_off):
    """몸통(셔츠). shoulder_logical, hip_logical 반환."""
    top = TORSO_TOP + y_off
    bot = TORSO_BOTTOM + y_off
    lx = lean * 0.6
    pts_outline = [(lx - SHOULDER_W - 3, top + 2), (lx + SHOULDER_W + 3, top),
                   (HIP_W + 3, bot), (-HIP_W - 2, bot)]
    d.polygon(pts_outline, fill=OUTLINE)
    d.polygon([(lx - SHOULDER_W, top + 3), (lx + SHOULDER_W, top + 1),
               (HIP_W - 1, bot - 1), (-HIP_W, bot)], fill=SHIRT)
    # 그늘
    d.polygon([(lx - SHOULDER_W + 4, top + 5), (lx + SHOULDER_W - 5, top + 3),
               (HIP_W - 4, bot - 2), (-HIP_W + 3, bot - 1)], fill=SHIRT_DARK)
    return (lx, top), (0, bot)


def draw_head(d, cx, cy, lean):
    """머리: 머리카락 + 얼굴 + 눈."""
    r = HEAD_R
    d.ellipse([cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3], fill=OUTLINE)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=SKIN)
    # 머리카락: 위쪽 반원
    d.chord([cx - r - 2, cy - r - 4, cx + r + 2, cy + r * 0.5], 180, 360, fill=HAIR)
    # 눈
    ey = cy + 3
    ex = lean * 0.3
    d.ellipse([cx - 7 + ex, ey - 4, cx - 1 + ex, ey + 4], fill=EYE)
    d.ellipse([cx + 2 + ex, ey - 4, cx + 8 + ex, ey + 4], fill=EYE)
    d.ellipse([cx - 6 + ex, ey - 3, cx - 4 + ex, ey - 1], fill=(255, 255, 255, 255))
    d.ellipse([cx + 3 + ex, ey - 3, cx + 5 + ex, ey - 1], fill=(255, 255, 255, 255))
    # 입
    d.arc([cx - 4 + ex, ey + 3, cx + 5 + ex, ey + 9], 20, 160,
          fill=(120, 70, 60, 255), width=2)


def draw_sword(d, hand, angle):
    """검: 손에서 각도 방향으로 뻗는 검."""
    hx, hy = hand
    dx, dy = rot(0, -1, angle)
    px, py = -dy, dx
    # 손잡이
    gx, gy = hx - dx * 7, hy - dy * 7
    d.line([(hx, hy), (gx, gy)], fill=OUTLINE, width=8)
    d.line([(hx, hy), (gx, gy)], fill=HILT, width=5)
    # 가드
    d.line([(gx - px * 5, gy - py * 5), (gx + px * 5, gy + py * 5)],
           fill=HILT, width=4)
    # 검신
    tipx, tipy = hx + dx * 38, hy + dy * 38
    d.polygon([(gx + px * 5, gy + py * 5), (tipx + px * 1.5, tipy + py * 1.5),
               (tipx - px * 1.5, tipy - py * 1.5), (gx - px * 5, gy - py * 5)],
              fill=BLADE_EDGE)
    d.polygon([(gx + px * 3, gy + py * 3), (tipx + px * 0.7, tipy + py * 0.7),
               (tipx - px * 0.7, tipy - py * 0.7), (gx - px * 3, gy - py * 3)],
              fill=BLADE)


# ---------------------------------------------------------------
# 프레임 렌더링
# ---------------------------------------------------------------
def render_pose(pose, kind):
    """포즈 1개를 고해상도 이미지로 렌더링.

    반환: (PIL.Image, bounds)  bounds = 논리 좌표계에서 사용된 최소/최대
    """
    lean, y_off, arm_angle = pose

    W = FRAME_W * SS
    H = FRAME_H * SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 논리 -> 픽셀 변환 헬퍼 (배율 SS, 바닥 y=GROUND_Y 기준)
    def P(px, py):
        return (px * SS, (GROUND_Y - py) * SS)

    def E(cx, cy, rx, ry=None):
        ry = rx if ry is None else ry
        x, y = P(cx, cy)
        return [x - rx * SS, y - ry * SS, x + rx * SS, y + ry * SS]

    # 그림자
    d.ellipse(E(0, 1, 20, 5), fill=(0, 0, 0, 45))

    shoulder, hip = draw_torso(d, lean, y_off)

    # 다리
    draw_leg(d, (-HIP_W, hip[1] + 2), -lean * 0.7, dark=True)
    draw_leg(d, (HIP_W, hip[1] + 2), lean, dark=False)

    # 머리
    draw_head(d, lean * 0.6, HEAD_CY + y_off, lean)

    # 팔
    sh_back = (shoulder[0] - SHOULDER_W, shoulder[1] + 2)
    sh_front = (shoulder[0] + SHOULDER_W, shoulder[1] + 2)
    draw_arm(d, sh_back, arm_angle * 0.6, dark=True)
    _, hand = draw_arm(d, sh_front, arm_angle, dark=False)

    if kind == "attack":
        draw_sword(d, hand, arm_angle)

    return img


def trim(img):
    """투명 영역을 제거하고 (bbox, 잘린 이미지) 반환."""
    bbox = img.getbbox()
    if bbox is None:
        return (0, 0, img.width, img.height), img
    return bbox, img.crop(bbox)
