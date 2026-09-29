"""
스프라이트 시트 검증 스크립트
=============================
animation_viewer.py 가 참조하는 시트/메타데이터가 올바른지 검사한다.

검사 항목
  1. 메타데이터 JSON 파싱 및 필수 키 존재
  2. 시트 PNG 파일 존재 및 로드 가능
  3. 각 프레임 사각형이 시트 범위 안에 있는지
  4. 프레임에 실제 픽셀이 그려져 있는지 (빈 프레임 방지)
  5. 인접 프레임의 투명 영역이 겹쳐 문자가 섞이지 않는지
  6. 앵커 좌표가 프레임 범위 안에 있는지
  7. 애니메이션마다 프레임 수가 서로 다른지 (과제 보너스 항목)

실행:  python verify_sheets.py
(실패 시 종료 코드 1)
"""

import json
import os
import sys

from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
META_PATH = os.path.join(BASE_DIR, "sheet_meta.json")

# 한 프레임에서 기대되는 최소 불투명 픽셀 수
MIN_OPAQUE = 500


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.notes = []

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def note(self, msg):
        self.notes.append(msg)

    def ok(self):
        return len(self.errors) == 0


def content_bbox(alpha, left, top, w, h, width, height):
    """지정 사각형 안에서 실제로 그려진 픽셀의 타이트 bbox."""
    px = alpha.load()
    x0, y0, x1, y1 = left + w, top + h, left, top
    for y in range(max(0, top), min(height, top + h)):
        for x in range(max(0, left), min(width, left + w)):
            if px[x, y] > 0:
                if x < x0:
                    x0 = x
                if x + 1 > x1:
                    x1 = x + 1
                if y < y0:
                    y0 = y
                if y + 1 > y1:
                    y1 = y + 1
    return x0, y0, x1, y1


def check_animation(anim, rep):
    """애니메이션 하나를 검증한다."""
    name = anim.get("name", "<이름없음>")
    path = os.path.join(BASE_DIR, anim.get("image", ""))

    for key in ("image", "fps", "frame_count", "frames"):
        if key not in anim:
            rep.error(f"{name}: 필수 키 '{key}' 없음")
    if not os.path.exists(path):
        rep.error(f"{name}: 시트 파일 없음 -> {anim.get('image')}")
        return
    if not anim.get("frames"):
        rep.error(f"{name}: 프레임 목록이 비어 있음")
        return

    im = Image.open(path).convert("RGBA")
    W, H = im.size
    alpha = im.getchannel("A")

    if anim["frame_count"] != len(anim["frames"]):
        rep.error(f"{name}: frame_count({anim['frame_count']}) != "
                  f"frames 길이({len(anim['frames'])})")
    if anim["fps"] <= 0:
        rep.error(f"{name}: fps 가 0 이하")

    boxes = []
    for f in anim["frames"]:
        idx = f.get("index")
        l, t, w, h = f["left"], f["top"], f["width"], f["height"]

        if l < 0 or t < 0 or l + w > W or t + h > H:
            rep.error(f"{name} #{idx}: 프레임 사각형이 시트 범위 밖 "
                      f"({l},{t},{w}x{h}) vs sheet {W}x{H}")
            continue

        crop = im.crop((l, t, l + w, t + h))
        opaque = sum(crop.getchannel("A").histogram()[1:])
        if opaque < MIN_OPAQUE:
            rep.error(f"{name} #{idx}: 빈 프레임 (불투명 픽셀 {opaque})")

        ax, ay = f.get("anchor_x"), f.get("anchor_y")
        if ax is None or ay is None:
            rep.error(f"{name} #{idx}: anchor 좌표 없음")
        elif not (0 <= ax <= w and 0 <= ay <= h):
            rep.error(f"{name} #{idx}: 앵커({ax},{ay})가 프레임({w}x{h}) 밖")

        boxes.append(content_bbox(alpha, l, t, w, h, W, H))

    for i in range(len(boxes) - 1):
        b0, b1 = boxes[i], boxes[i + 1]
        overlap_x = min(b0[2], b1[2]) - max(b0[0], b1[0])
        overlap_y = min(b0[3], b1[3]) - max(b0[1], b1[1])
        if overlap_x > 0 and overlap_y > 0:
            rep.error(f"{name}: #{i} 와 #{i+1} 의 그림자가 겹침 "
                      f"({overlap_x}x{overlap_y}px)")


def main():
    rep = Report()

    if not os.path.exists(META_PATH):
        print(f"[X] 메타데이터 없음: {META_PATH}")
        print("    make_sprite_sheet.py 를 먼저 실행하세요.")
        return 1

    with open(META_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    anims = data.get("animations", [])
    if not anims:
        rep.error("애니메이션이 하나도 없음")
    if len(anims) < 4:
        rep.warn(f"애니메이션이 {len(anims)}개 입니다 (과제 요구: 4종 이상)")

    for anim in anims:
        check_animation(anim, rep)

    # 보너스 항목: 애니메이션별 프레임 수가 서로 다른가
    counts = {a.get("name"): a.get("frame_count") for a in anims}
    if len(set(counts.values())) == len(counts):
        rep.note(f"프레임 수 모두 다름 (보너스): {counts}")
    else:
        rep.warn(f"프레임 수가 중복됨: {counts}")

    # 보너스 항목: 프레임 크기가 프레임마다 다른가
    for anim in anims:
        sizes = {(f["width"], f["height"]) for f in anim["frames"]}
        if len(sizes) > 1:
            rep.note(f"{anim['name']}: 프레임 크기 {len(sizes)}종 (가변 스프라이트 시트)")
        else:
            rep.warn(f"{anim['name']}: 모든 프레임 크기가 동일")

    print("=" * 58)
    for n in rep.notes:
        print(f"[OK] {n}")
    for wmsg in rep.warnings:
        print(f"[!] {wmsg}")
    for emsg in rep.errors:
        print(f"[X] {emsg}")
    print("=" * 58)

    if rep.ok():
        print("검증 통과: 모든 시트가 정상입니다.")
        return 0
    print(f"검증 실패: 오류 {len(rep.errors)}건")
    return 1


if __name__ == "__main__":
    sys.exit(main())
