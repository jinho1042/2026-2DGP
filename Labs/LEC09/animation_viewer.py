"""
애니메이션 뷰어 (LEC09 과제)
===========================
sonic-sprite.png 에서 추출한 모든 애니메이션을 순차 재생한다.

- 각 애니메이션은 5회 반복한 뒤 1회 더 재생하고 다음으로 넘어간다.
- 마지막 애니메이션까지 마치면 처음부터 무한 반복한다.
- 1200 x 800 창에 프레임을 크게 표시한다.

실행:  python animation_viewer.py
"""

import json
import os

import pico2d

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
META_PATH = os.path.join(BASE_DIR, "sheet_meta.json")

CANVAS_W, CANVAS_H = 1200, 800


def find_font(size):
    """표시용 TrueType 폰트를 찾는다. 없으면 None 을 돌려준다."""
    for path in (
        r"C:\Windows\Fonts\malgun.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
    ):
        if os.path.exists(path):
            try:
                return pico2d.load_font(path, size)
            except Exception:
                return None
    return None


def load_meta():
    """메타데이터를 읽는다. 없으면 안내 후 종료한다."""
    if not os.path.exists(META_PATH):
        print("=" * 58)
        print("sheet_meta.json 이 없습니다.")
        print("먼저 아래 명령을 실행하세요:")
        print("    python sheet_parser.py")
        print("=" * 58)
        raise SystemExit(1)

    with open(META_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def set_window_title(title):
    """창 제목을 설정한다. 실패해도 재생은 계속한다."""
    try:
        import pico2d.pico2d as _p2
        pico2d.SDL_SetWindowTitle(_p2.window, title.encode("utf-8"))
    except Exception as exc:
        print("창 제목 설정 생략:", exc)


def main():
    meta = load_meta()
    sheet = pico2d.load_image(os.path.join(BASE_DIR, meta["image"]))
    print(f"시트 {meta['image']}  애니메이션 {meta['animation_count']}개 "
          f"프레임 {meta['total_frames']}개")

    pico2d.open_canvas(CANVAS_W, CANVAS_H)
    set_window_title("LEC09 Animation Viewer")

    running = True
    while running:
        for event in pico2d.get_events():
            if event.type == pico2d.SDL_QUIT:
                running = False
            elif event.type == pico2d.SDL_KEYDOWN:
                if event.key == pico2d.SDLK_ESCAPE:
                    running = False

        pico2d.clear_canvas()
        pico2d.update_canvas()

    pico2d.close_canvas()


if __name__ == "__main__":
    main()
