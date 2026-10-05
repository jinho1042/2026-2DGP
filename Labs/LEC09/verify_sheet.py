"""
메타데이터 검증 도구 (LEC09 과제)
==============================
sheet_meta.json 이 시트 이미지와 실제로 맞는지 확인한다.

- 모든 프레임 사각형이 시트 범위 안에 있는가
- 프레임 간 좌표가 겹치지 않는가
- 시트 픽셀을 다시 읽어 각 프레임 영역에 그림이 존재하는가
- 애니메이션/프레임 개수가 선언값과 일치하는가

실행:  python verify_sheet.py
"""

import json
import os
import sys

from sheet_parser import (
    META_PATH,
    SHEET_PATH,
    alpha_mask,
    load_pixels,
)

TOLERANCE = 0.30
"""프레임 영역 안에서 그림이 있어야 하는 최소 비율.

소닉 계열 스프라이트는 몸통이 가늘고 다리가 뻗어 있어서
프레임 사각형의 4~5割만 차지한다. 3割 미만이면 좌표가 어긋난 것."""


def load_meta(path=META_PATH):
    """메타데이터를 읽는다."""
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def check_bounds(meta):
    """모든 프레임이 시트 범위 안에 있는지 검사한다."""
    width = meta["sheet_width"]
    height = meta["sheet_height"]
    problems = []

    for animation in meta["animations"]:
        for frame in animation["frames"]:
            left, top = frame["left"], frame["top"]
            right = left + frame["width"]
            bottom = top + frame["height"]
            if left < 0 or top < 0 or right > width or bottom > height:
                problems.append(
                    f"{animation['name']} #{frame['index']}: "
                    f"범위 초과 ({left},{top})-({right},{bottom}) "
                    f"시트 {width}x{height}"
                )
    return problems


def check_overlap(meta):
    """같은 시퀀스 안에서 프레임 사각형이 겹치지 않는지 검사한다."""
    problems = []

    for animation in meta["animations"]:
        frames = animation["frames"]
        for i, a in enumerate(frames):
            for b in frames[i + 1:]:
                if (a["left"] < b["left"] + b["width"] and
                        b["left"] < a["left"] + a["width"] and
                        a["top"] < b["top"] + b["height"] and
                        b["top"] < a["top"] + a["height"]):
                    problems.append(
                        f"{animation['name']}: "
                        f"#{a['index']} 과 #{b['index']} 가 겹침"
                    )
    return problems


def check_coverage(meta, sheet_path=SHEET_PATH):
    """각 프레임 영역에 실제로 그림이 있는지 검사한다."""
    width, height, pixels = load_pixels(sheet_path)
    mask = alpha_mask(width, height, pixels)
    problems = []
    stats = []

    for animation in meta["animations"]:
        for frame in animation["frames"]:
            left, top = frame["left"], frame["top"]
            fw, fh = frame["width"], frame["height"]

            painted = 0
            for y in range(top, top + fh):
                row = y * width
                for x in range(left, left + fw):
                    if mask[row + x]:
                        painted += 1

            ratio = painted / (fw * fh)
            stats.append((animation["name"], frame["index"], ratio))
            if ratio < TOLERANCE:
                problems.append(
                    f"{animation['name']} #{frame['index']}: "
                    f"채움률 {ratio:.0%} 가 기준 {TOLERANCE:.0%} 미달"
                )
    return problems, stats


def check_counts(meta):
    """선언된 개수가 실제 배열 길이와 맞는지 검사한다."""
    problems = []

    if meta["animation_count"] != len(meta["animations"]):
        problems.append(
            f"애니메이션 수 불일치: {meta['animation_count']} "
            f"!= {len(meta['animations'])}"
        )

    total = 0
    for animation in meta["animations"]:
        if animation["frame_count"] != len(animation["frames"]):
            problems.append(
                f"{animation['name']}: 프레임 수 불일치 "
                f"{animation['frame_count']} != {len(animation['frames'])}"
            )
        total += len(animation["frames"])

    if meta["total_frames"] != total:
        problems.append(
            f"총 프레임 수 불일치: {meta['total_frames']} != {total}"
        )
    return problems


def main():
    if not os.path.exists(META_PATH):
        print(f"메타데이터 없음: {META_PATH}")
        print("먼저 실행하세요:  python sheet_parser.py")
        return 1

    meta = load_meta()

    print(f"시트        : {meta['image']} "
          f"({meta['sheet_width']} x {meta['sheet_height']})")
    print(f"애니메이션  : {meta['animation_count']}개")
    print(f"총 프레임  : {meta['total_frames']}개")
    print("-" * 58)

    problems = []
    problems += check_counts(meta)
    print(f"[{'OK' if not problems else 'FAIL'}] 개수 일치성")
    count_problems = len(problems)

    bounds = check_bounds(meta)
    problems += bounds
    print(f"[{'OK' if not bounds else 'FAIL'}] 시트 범위")
    print(f"[{'OK' if not bounds else 'FAIL'}] 프레임 겹침")
    problems += check_overlap(meta)

    coverage, stats = check_coverage(meta)
    problems += coverage
    ratios = [r for _, _, r in stats]
    print(f"[{'OK' if not coverage else 'FAIL'}] 프레임 채움률 "
          f"(최소 {min(ratios):.0%}, 평균 {sum(ratios)/len(ratios):.0%})")

    print("-" * 58)
    if problems:
        print(f"문제 {len(problems)}건:")
        for problem in problems[:20]:
            print(f"  - {problem}")
        return 1

    print("모든 검사 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
