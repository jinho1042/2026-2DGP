"""
스프라이트 시트 생성기
=====================
4종 애니메이션(걷기 / 뛰기 / 점프 / 공격)을 PNG 시트로 생성한다.

- animation_viewer.py 가 불러올 PNG 와 JSON 메타데이터를 만든다.
- 프레임마다 크기가 다른 "복잡한 스프라이트 시트"를 만들기 위해
  각 프레임을 개별 캔버스에 렌더링 후 가변 크기로 시트에 배치한다.
- 실행:  python make_sprite_sheet.py

좌표 규약
---------
논리 좌표: 발밑이 y=0, 위쪽이 +y (캐릭터 관절 계산용)
픽셀 좌표: Pillow ImageDraw 규약 그대로 (왼쪽 위 기준, y 아래쪽이 +)
변환은 l2p() 한 곳에서만 수행한다.
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
        # 6 프레임
        "name": "walk",
        "fps": 8,
        "poses": [
            (0, 0, 18), (0, -2, 0), (0, 0, -18),
            (0, -2, 0), (0, 0, 18), (0, -2, 0),
        ],
    },
    {
        # 8 프레임
        "name": "run",
        "fps": 14,
        "poses": [
            (26, 0, 38), (22, -8, 26), (13, -4, 8), (5, -10, -8),
            (0, -5, -22), (5, 0, -32), (13, -8, -26), (22, -4, -8),
        ],
    },
    {
        # 5 프레임
        "name": "jump",
        "fps": 6,
        "poses": [
            (0, 16, -28), (7, 32, -20), (-9, -36, 22),
            (0, -14, 12), (0, 0, 0),
        ],
    },
    {
        # 7 프레임
        "name": "attack",
        "fps": 11,
        "poses": [
            (0, 0, -52), (0, -4, -68), (8, -7, -34), (17, -5, 22),
            (23, 0, 56), (15, 4, 74), (5, 0, 44),
        ],
    },
]

# ---------------------------------------------------------------
# 팔레트
# ---------------------------------------------------------------
SKIN = (247, 214, 174, 255)
SKIN_DARK = (206, 174, 138, 255)
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
# 캐릭터 기하 (논리 좌표)
# 캐릭터 머리 정수리까지의 높이 = 104, 발밑 = 0 근처
# ---------------------------------------------------------------
HEAD_R = 15
HEAD_CY = 86
SHOULDER_W = 11
HIP_W = 8
TORSO_TOP = 70
TORSO_BOTTOM = 40
UPPER_ARM = 17
FORE_ARM = 16
THIGH = 18
SHIN = 18
FOOT = 12
SWORD_LEN = 40

# 프레임 논리 크기
# 공격 애니메이션의 검 끝(최고점 y≈145)까지 들어오게 여유를 둔다.
FRAME_W = 170
FRAME_H = 180
GROUND_Y = 160         # 발밑 위치 (논리) — 프레임 하단 근처
CENTER_X = FRAME_W / 2 # 캐릭터 가로 중심 (논리)

SS = 4                # 슈퍼샘플링 배율
PAD = 8               # 시트 내 프레임 간 여백 (픽셀)
DOWNSCALE = 2         # SS -> 최종 축소 배율


def l2p(x, y):
    """논리 좌표 -> 픽셀 좌표. (발밑 y=GROUND_Y, 가로 중앙 기준, y 반전)"""
    return ((CENTER_X + x) * SS, (GROUND_Y - y) * SS)


def s(v):
    """길이 스케일."""
    return v * SS


def rot(x, y, deg):
    rad = math.radians(deg)
    c, sn = math.cos(rad), math.sin(rad)
    return x * c - y * sn, x * sn + y * c


def _seg(d, a, b, color, width):
    """선분 1개 (논리 좌표 입력)."""
    d.line([l2p(*a), l2p(*b)], fill=color, width=int(s(width)), joint="curve")


def _poly(d, pts, color):
    d.polygon([l2p(*p) for p in pts], fill=color)


def _box(x0, y0, x1, y1):
    """논리 좌표 사각형 -> 픽셀 bbox (좌표 뒤집힘 처리)."""
    ax, ay = l2p(x0, y0)
    bx, by = l2p(x1, y1)
    return [min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)]


def _circle(d, c, r, color, ry=None):
    ry = r if ry is None else ry
    x, y = l2p(*c)
    rx = s(r)
    ryv = s(ry)
    d.ellipse([x - rx, y - ryv, x + rx, y + ryv], fill=color)


# ---------------------------------------------------------------
# 파츠 드로잉 (모두 논리 좌표 입력)
# ---------------------------------------------------------------
def draw_leg(d, hip, angle, dark=False):
    """다리: 허벅지 + 정강이 + 신발. (무릎, 발목) 반환."""
    ox, oy = hip
    color = PANTS_DARK if dark else PANTS
    mx = ox + rot(0, -THIGH, angle)[0]
    my = oy + rot(0, -THIGH, angle)[1]
    fx = mx + rot(0, -SHIN, angle * 0.3)[0]
    fy = my + rot(0, -SHIN, angle * 0.3)[1]

    for a, b in (((ox, oy), (mx, my)), ((mx, my), (fx, fy))):
        _seg(d, a, b, OUTLINE, 12)
    for a, b in (((ox, oy), (mx, my)), ((mx, my), (fx, fy))):
        _seg(d, a, b, color, 8)
    _circle(d, (mx, my), 5, color)

    tx, ty = rot(FOOT * 0.6, -3, angle)
    hx, hy = rot(-FOOT * 0.4, -3, angle)
    _seg(d, (fx + hx, fy + hy), (fx + tx, fy + ty), OUTLINE, 13)
    _seg(d, (fx + hx, fy + hy), (fx + tx, fy + ty), SHOE, 9)
    return (mx, my), (fx, fy)


def draw_arm(d, shoulder, angle, dark=False):
    """팔: 위팔 + 전완 + 손. (팔꿈치, 손) 반환."""
    ox, oy = shoulder
    color = SKIN_DARK if dark else SKIN
    ex = ox + rot(0, -UPPER_ARM, angle)[0]
    ey = oy + rot(0, -UPPER_ARM, angle)[1]
    hx = ex + rot(0, -FORE_ARM, angle * 0.4)[0]
    hy = ey + rot(0, -FORE_ARM, angle * 0.4)[1]
    for a, b in (((ox, oy), (ex, ey)), ((ex, ey), (hx, hy))):
        _seg(d, a, b, OUTLINE, 10)
    for a, b in (((ox, oy), (ex, ey)), ((ex, ey), (hx, hy))):
        _seg(d, a, b, color, 6)
    _circle(d, (hx, hy), 5, OUTLINE)
    _circle(d, (hx, hy), 3.5, color)
    return (ex, ey), (hx, hy)


def draw_torso(d, lean, y_off):
    """몸통(셔츠). (어깨 중심, 골반) 논리 좌표 반환."""
    top = TORSO_TOP + y_off
    bot = TORSO_BOTTOM + y_off
    lx = lean * 0.6
    _poly(d, [(lx - SHOULDER_W - 3, top + 2), (lx + SHOULDER_W + 3, top),
              (HIP_W + 3, bot), (-HIP_W - 2, bot)], OUTLINE)
    _poly(d, [(lx - SHOULDER_W, top + 3), (lx + SHOULDER_W, top + 1),
              (HIP_W - 1, bot - 1), (-HIP_W, bot)], SHIRT)
    _poly(d, [(lx - SHOULDER_W + 4, top + 5), (lx + SHOULDER_W - 5, top + 3),
              (HIP_W - 4, bot - 2), (-HIP_W + 3, bot - 1)], SHIRT_DARK)
    return (lx, top), (0, bot)


def draw_head(d, cx, cy, lean):
    """머리: 머리카락 + 얼굴 + 눈."""
    r = HEAD_R
    _circle(d, (cx, cy), r + 3, OUTLINE)
    _circle(d, (cx, cy), r, SKIN)
    # 머리카락 (윗부분 반원) - outline 을 살짝 넘겨 덮는다
    _circle(d, (cx, cy + 2), r + 2, HAIR, ry=r + 4)
    _circle(d, (cx, cy), r, SKIN)
    ey = cy + 4
    ex = lean * 0.3
    _circle(d, (cx - 4 + ex, ey), 2.6, EYE, ry=3.2)
    _circle(d, (cx + 5 + ex, ey), 2.6, EYE, ry=3.2)
    _circle(d, (cx - 4.6 + ex, ey + 1), 1.0, (255, 255, 255, 255), ry=1.2)
    _circle(d, (cx + 4.4 + ex, ey + 1), 1.0, (255, 255, 255, 255), ry=1.2)
    # 입
    d.arc(_box(cx - 4 + ex, ey + 5, cx + 6 + ex, ey + 10),
          20, 160, fill=(120, 70, 60, 255), width=max(1, int(s(0.7))))


def draw_sword(d, hand, angle):
    """검: 손에서 angle 방향으로 뻗는 검."""
    hx, hy = hand
    dx, dy = rot(0, -1, angle)
    px, py = -dy, dx
    gx, gy = hx - dx * 8, hy - dy * 8
    _seg(d, (hx, hy), (gx, gy), OUTLINE, 7)
    _seg(d, (hx, hy), (gx, gy), HILT, 4.5)
    _seg(d, (gx - px * 6, gy - py * 6), (gx + px * 6, gy + py * 6), HILT, 4)
    tipx, tipy = hx + dx * SWORD_LEN, hy + dy * SWORD_LEN
    _poly(d, [(gx + px * 6, gy + py * 6), (tipx + px * 2, tipy + py * 2),
              (tipx - px * 2, tipy - py * 2), (gx - px * 6, gy - py * 6)], BLADE_EDGE)
    _poly(d, [(gx + px * 3.5, gy + py * 3.5), (tipx + px * 0.9, tipy + py * 0.9),
              (tipx - px * 0.9, tipy - py * 0.9), (gx - px * 3.5, gy - py * 3.5)], BLADE)


# ---------------------------------------------------------------
# 프레임 렌더링
# ---------------------------------------------------------------
def render_pose(pose, kind):
    """포즈 1개를 고해상도 RGBA 이미지로 렌더링."""
    lean, y_off, arm_angle = pose

    img = Image.new("RGBA", (FRAME_W * SS, FRAME_H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 발밑 그림자
    _circle(d, (0, 1), 20, (0, 0, 0, 45), ry=5)

    shoulder, hip = draw_torso(d, lean, y_off)

    # 다리 (뒤 -> 앞)
    draw_leg(d, (-HIP_W, hip[1] + 2), -lean * 0.7, dark=True)
    draw_leg(d, (HIP_W, hip[1] + 2), lean, dark=False)

    # 머리
    draw_head(d, lean * 0.6, HEAD_CY + y_off, lean)

    # 팔 (뒤 -> 앞)
    draw_arm(d, (shoulder[0] - SHOULDER_W, shoulder[1] + 2), arm_angle * 0.6, dark=True)
    _, hand = draw_arm(d, (shoulder[0] + SHOULDER_W, shoulder[1] + 2),
                       arm_angle, dark=False)

    if kind == "attack":
        draw_sword(d, hand, arm_angle)

    return img


def trim(img):
    """투명 영역 제거. (bbox, 크롭 이미지) 반환."""
    bbox = img.getbbox()
    if bbox is None:
        return (0, 0, img.width, img.height), img
    return bbox, img.crop(bbox)


# ---------------------------------------------------------------
# 시트 조립 (프레임마다 크기가 다르다)
# ---------------------------------------------------------------
def build_sheet(anim):
    """한 애니메이션 시트 생성. (시트 이미지, 프레임 메타 리스트) 반환.

    프레임마다 크기가 다르므로(가변 스프라이트 시트), 동일 여백으로 배치하되
    각 프레임 안에서 '발밑 지점'이 어디인지 anchor_x/anchor_y 로 기록한다.
    뷰어는 이 앵커를 기준으로 화면 좌표를 계산하므로 포즈가 달라도
    캐릭터가 같은 바닥선 위에 자연스럽게 정렬된다.
    """
    name = anim["name"]
    rendered = []
    for i, pose in enumerate(anim["poses"]):
        hi = render_pose(pose, name)
        bbox, cropped = trim(hi)
        frame = cropped.resize((cropped.width // DOWNSCALE,
                                cropped.height // DOWNSCALE), Image.LANCZOS)
        # 발밑(논리 x=0, y=0) 지점이 크롭된 이미지 안의 어디인지
        # ax: 왼쪽에서부터 거리, ay: 위에서부터 거리
        ax = (CENTER_X * SS - bbox[0]) / DOWNSCALE
        ay = (GROUND_Y * SS - bbox[1]) / DOWNSCALE
        rendered.append({"index": i, "img": frame, "ax": ax, "ay": ay})

    # 동일 여백 가로 배치 (프레임 사각형이 겹치지 않도록)
    meta = []
    cursor = PAD
    for r in rendered:
        frame = r["img"]
        meta.append({
            "index": r["index"],
            "left": cursor,
            "top": PAD,
            "width": frame.width,
            "height": frame.height,
            "anchor_x": round(r["ax"], 2),
            "anchor_y": round(r["ay"], 2),
        })
        cursor += frame.width + PAD

    sheet_w = cursor
    sheet_h = PAD + max(r["img"].height for r in rendered) + PAD
    sheet = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))
    for r, m in zip(rendered, meta):
        sheet.paste(r["img"], (m["left"], m["top"]), r["img"])
    return sheet, meta


def main():
    all_meta = []
    for anim in ANIMATIONS:
        sheet, meta = build_sheet(anim)
        fname = f"sheet_{anim['name']}.png"
        sheet.save(os.path.join(OUT_DIR, fname))
        all_meta.append({
            "name": anim["name"],
            "image": fname,
            "fps": anim["fps"],
            "frame_count": len(anim["poses"]),
            "frames": meta,
        })
        print(f"[+] {fname}  {sheet.width}x{sheet.height}  frames={len(meta)}")

    with open(os.path.join(OUT_DIR, "sheet_meta.json"), "w", encoding="utf-8") as f:
        json.dump({"animations": all_meta}, f, ensure_ascii=False, indent=2)
    print(f"[+] sheet_meta.json  animations={len(all_meta)}")


if __name__ == "__main__":
    main()
