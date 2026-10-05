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


def check_player():
    """Player 상태 전이가 PRD 규칙(5회 반복 + 1회)을 지키는지 검사한다.

    실제 렌더링 없이 시간만 흘려보내 규칙을 검증한다.
    """
    import animation_viewer as av

    class _FakeSheet:
        h = 525

    meta = load_meta()
    player = av.Player(av.load_animations(meta, _FakeSheet()))

    problems = []

    # anim_01 은 프레임이 10개이므로 반복 6회를 관찰하려면 충분히 돌린다.
    first = player.current.count
    seen_repeats = set()
    ticks = 0
    while player.anim_index == 0 and ticks < 100000:
        player.update(1.0 / 60.0)
        seen_repeats.add(player.repeat)
        ticks += 1

    expected = set(range(av.REPEAT_COUNT + 1))
    if seen_repeats != expected:
        problems.append(
            f"반복 횟수 규칙 위반: {sorted(seen_repeats)} != {sorted(expected)}"
        )
    if player.anim_index != 1:
        problems.append(
            f"첫 애니메이션 종료 후 다음으로 넘어가지 않음: "
            f"anim_index={player.anim_index}"
        )

    # 전체 시퀀스를 한 바퀴 돌면 처음 anim 으로 돌아오고 cycles 가 증가한다.
    before = player.cycles
    for _ in range(200000):
        player.update(1.0 / 60.0)
        if player.cycles > before:
            break
    if player.cycles <= before:
        problems.append("전체 시퀀스 순회 후 처음으로 돌아가지 않음")
    if player.anim_index != 0:
        problems.append(f"한 바퀴 후 anim_index 가 0 이 아님: {player.anim_index}")

    return problems, first, ticks


def check_render():
    """실제로 캔버스를 열어 모든 프레임이 그려지는지 확인한다.

    창을 띄울 수는 없으므로 환경변수로 헤드리스 렌더러를 쓰며,
    그래도 실패하면 문제가 있다고 보고한다.
    """
    try:
        import animation_viewer as av
    except Exception as exc:      # 뷰어는 pico2d 가 필요해 관대하게 처리
        return [f"뷰어 모듈 로드 실패: {exc}"]

    problems = []
    try:
        meta = load_meta()
        av.pico2d.open_canvas(av.CANVAS_W, av.CANVAS_H)
        try:
            sheet = av.pico2d.load_image(
                os.path.join(av.BASE_DIR, meta["image"]))
            animations = av.load_animations(meta, sheet)
            fonts = (av.find_font(44), av.find_font(20), av.find_font(16))
            player = av.Player(animations)
            state = {"flip": False, "paused": False, "step_mode": False,
                     "scale": 1.0, "fps": 12, "overlay": True}

            for animation in animations:
                for position in range(animation.count):
                    av.pico2d.clear_canvas()
                    av.draw_background()
                    av.draw_frame(animation, position, False, 1.0)
                    av.draw_frame(animation, position, True, 0.5)
                    av.draw_strip(animation, position)
                    av.draw_sheet_overlay(animation, position)
                    av.draw_ui(fonts, player, state)
                    av.pico2d.update_canvas()
        finally:
            av.pico2d.close_canvas()
    except Exception as exc:
        problems.append(f"렌더링 실패: {exc}")

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

    bounds = check_bounds(meta)
    problems += bounds
    print(f"[{'OK' if not bounds else 'FAIL'}] 시트 범위")

    overlaps = check_overlap(meta)
    problems += overlaps
    print(f"[{'OK' if not overlaps else 'FAIL'}] 프레임 겹침")

    coverage, stats = check_coverage(meta)
    problems += coverage
    ratios = [ratio for _, _, ratio in stats]
    print(f"[{'OK' if not coverage else 'FAIL'}] 프레임 채움률 "
          f"(최소 {min(ratios):.0%}, 평균 {sum(ratios)/len(ratios):.0%})")

    player_problems, frames, ticks = check_player()
    problems += player_problems
    print(f"[{'OK' if not player_problems else 'FAIL'}] 재생 규칙 "
          f"(anim_01 {frames} 프레임 x 6회 = {ticks}틱 후 전환)")

    render_problems = check_render()
    problems += render_problems
    print(f"[{'OK' if not render_problems else 'FAIL'}] 전체 프레임 렌더링")

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
