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

REPEAT_COUNT = 5
"""각 애니메이션을 반복 재생할 횟수."""

FRAME_DURATION = 1.0 / 12
"""프레임 하나를 화면에 유지하는 시간(초)."""


class Animation:
    """애니메이션 하나: 시트 이미지 + 프레임 사각형 목록."""

    def __init__(self, data, sheet):
        self.name = data["name"]
        self.index = data["index"]
        self.fps = data["fps"]
        self.frames = data["frames"]
        self.count = len(self.frames)
        self.sheet = sheet
        self.sheet_h = sheet.h

    def frame(self, position):
        """프레임 정보를 인덱스 순환으로 돌려준다."""
        return self.frames[position % self.count]

    def clip_rect(self, position):
        """pico2d 용 (left, bottom, width, height) 사각형으로 변환한다.

        이 pico2d 빌드의 clip_composite_draw 는 bottom 이
        '이미지 아랫면으로부터의 거리'를 받는다.
        메타데이터는 시트 좌표의 top 이므로 변환이 필요하다.
        """
        info = self.frame(position)
        bottom = self.sheet_h - info["top"] - info["height"]
        return info["left"], bottom, info["width"], info["height"]


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


def load_animations(meta, sheet):
    """메타데이터로부터 Animation 리스트를 만든다."""
    return [Animation(data, sheet) for data in meta["animations"]]


FOOT_X = CANVAS_W / 2
FOOT_Y = CANVAS_H / 2
CHAR_HEIGHT = 320
"""화면에 표시할 캐릭터의 세로 크기(픽셀)."""

BG_TOP = (30, 34, 46, 255)
BG_BOTTOM = (18, 20, 28, 255)
GROUND = (44, 48, 64, 255)
GROUND_LINE = (96, 108, 140, 255)


def draw_background():
    """배경 그라데이션과 바닥을 그린다.

    스프라이트 시트에 그림자가 포함되어 있지 않으므로
    캐릭터 발밑에 타원을 하나 깔아 접지감을 준다.
    """
    band = 8
    top = CANVAS_H // 2 + 100
    for offset in range(0, top, band):
        ratio = offset / max(top - band, 1)
        color = tuple(
            int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * ratio)
            for i in range(3)
        )
        pico2d.draw_rectangle(0, offset, CANVAS_W, offset + band,
                              *color, 255, True)

    pico2d.draw_rectangle(0, 0, CANVAS_W, top, *BG_BOTTOM, 255, True)
    pico2d.draw_rectangle(0, 0, CANVAS_W, top - 2, *GROUND_LINE, 255, True)

    # 캐릭터 그림자
    pico2d.draw_ellipse((FOOT_X - 150, top - 14, FOOT_X + 150, top + 14),
                       20, 22, 32, 255)


LABEL = (236, 240, 248, 255)
SUB_LABEL = (146, 156, 180, 255)
ACCENT = (120, 200, 255, 255)

KEY_HELP = ("SPACE 일시정지 | . , 한 프레임 | N 다음 동작 | R 처음부터 | "
            "LEFT/RIGHT 방향 전환 | UP/DOWN 크기 | 0 기본 | ESC 종료")


def draw_ui(fonts, player, paused, step_mode, scale_ratio):
    """상단 상태 바와 하단 도움말을 그린다."""
    title_font, info_font, small_font = fonts
    if not info_font:
        return

    # 상단 상태 바
    pico2d.draw_rectangle(0, CANVAS_H - 104, CANVAS_W, CANVAS_H,
                          16, 18, 26, 190, True)
    pico2d.draw_rectangle(0, CANVAS_H - 104, CANVAS_W, CANVAS_H - 102,
                          *ACCENT, 255, True)

    animation = player.current

    if title_font:
        order = f"{player.anim_index + 1} / {len(player.animations)}"
        title_font.draw(CANVAS_W / 2, CANVAS_H - 46, animation.name,
                        LABEL[:3], align="center")
        title_font.draw(CANVAS_W - 130, CANVAS_H - 46, order,
                        SUB_LABEL[:3], align="right")

    mode = "정지" if paused else ("프레임" if step_mode else "재생")
    info_font.draw(CANVAS_W / 2, CANVAS_H - 74, player.status_text(),
                   SUB_LABEL[:3], align="center")
    info_font.draw(40, CANVAS_H - 74, f"모드 {mode}", SUB_LABEL[:3])

    # 반복 진행 표시: 6칸(5회 반복 + 1회 추가)
    bar_w, bar_h, gap = 26, 8, 8
    total_w = bar_w * (REPEAT_COUNT + 1) + gap * REPEAT_COUNT
    bx = CANVAS_W / 2 - total_w / 2
    for i in range(REPEAT_COUNT + 1):
        filled = i <= player.repeat
        color = ACCENT if filled else (52, 58, 76, 255)
        if i == REPEAT_COUNT and not filled:
            color = (90, 70, 52, 255)
        pico2d.draw_rectangle(bx, CANVAS_H - 92, bx + bar_w, CANVAS_H - 84,
                              *color, 255, True)
        bx += bar_w + gap

    if small_font:
        small_font.draw(CANVAS_W / 2, CANVAS_H - 118, KEY_HELP,
                        SUB_LABEL[:3], align="center")
        small_font.draw(40, 34,
                        f"크기 {scale_ratio:.0%}   "
                        f"프레임 {animation.frame(player.frame)['width']}x"
                        f"{animation.frame(player.frame)['height']}",
                        SUB_LABEL[:3])


ZOOM_STEP = 0.1
MIN_ZOOM = 0.5
MAX_ZOOM = 1.6


def handle_events(player, state):
    """키보드 이벤트를 처리한다. 종료 요청 시 False 를 반환한다."""
    for event in pico2d.get_events():
        if event.type == pico2d.SDL_QUIT:
            return False
        if event.type != pico2d.SDL_KEYDOWN:
            continue

        key = event.key

        if key == pico2d.SDLK_ESCAPE:
            return False
        elif key == pico2d.SDLK_SPACE:
            state["paused"] = player.toggle_pause()
            state["step_mode"] = False
        elif key == pico2d.SDLK_PERIOD:
            player.step_frame(1)
            state["paused"] = True
            state["step_mode"] = True
        elif key == pico2d.SDLK_COMMA:
            player.step_frame(-1)
            state["paused"] = True
            state["step_mode"] = True
        elif key == pico2d.SDLK_n:
            player.skip_next()
        elif key == pico2d.SDLK_r:
            player.reset()
            state["step_mode"] = False
        elif key == pico2d.SDLK_LEFT:
            state["flip"] = True
        elif key == pico2d.SDLK_RIGHT:
            state["flip"] = False
        elif key == pico2d.SDLK_UP:
            state["scale"] = min(state["scale"] + ZOOM_STEP, MAX_ZOOM)
        elif key == pico2d.SDLK_DOWN:
            state["scale"] = max(state["scale"] - ZOOM_STEP, MIN_ZOOM)
        elif key == pico2d.SDLK_0:
            state["scale"] = 1.0

    return True


def draw_strip(animation, current_frame):
    """현재 애니메이션의 전체 프레임을 아래쪽 줄로 보여준다.

    어느 프레임이 몇 번째인지 눈으로 확인할 수 있게 하는 것이 목적이며,
    지금 재생 중인 프레임은 강조 색으로 표시한다.
    """
    count = animation.count
    cell = 54
    gap = 8
    thumb = 40
    total_w = count * cell + (count - 1) * gap
    x = CANVAS_W / 2 - total_w / 2
    bottom = 86

    for i in range(count):
        info = animation.frame(i)
        scale = thumb / info["height"]
        w = info["width"] * scale
        h = info["height"] * scale

        active = i == current_frame
        box_color = ACCENT if active else (48, 54, 72, 255)
        pico2d.draw_rectangle(x, bottom - cell, x + cell, bottom,
                              *box_color, 255, True)

        animation.sheet.clip_composite_draw(
            *animation.clip_rect(i),
            0, "",
            x + cell / 2, bottom - cell / 2,
            w, h,
        )
        x += cell + gap


def frame_scale(animation):
    """프레임 원본 높이를 기준으로 화면 배율을 계산한다."""
    tallest = max(frame["height"] for frame in animation.frames)
    return CHAR_HEIGHT / tallest


def draw_frame(animation, position, flip=False, zoom=1.0):
    """현재 프레임을 화면 중앙에 크게 그린다.

    clip_composite_draw 의 (cx, cy) 는 목적지 사각형의 중심 좌표다.
    프레임마다 높이가 다르므로, 표시 높이를 일정하게 유지하도록
    프레임 세로 중앙이 같은 높이에 오게 중심을 계산한다.
    zoom 은 사용자가 조절하는 추가 배율이다.
    """
    info = animation.frame(position)
    scale = frame_scale(animation) * zoom

    dw = info["width"] * scale
    dh = info["height"] * scale

    left, bottom, width, height = animation.clip_rect(position)
    cy = FOOT_Y - CHAR_HEIGHT * zoom / 2 + dh / 2

    animation.sheet.clip_composite_draw(
        left, bottom, width, height,
        0, "h" if flip else "",
        FOOT_X, cy,
        dw, dh,
    )


class Player:
    """애니메이션 재생 상태를 관리한다.

    진행 규칙 (PRD 요구사항):
        각 애니메이션을 5회 반복한 뒤 1회 더 재생하고 다음으로 넘어간다.
        마지막 애니메이션까지 마치면 처음부터 무한 반복한다.
    """

    def __init__(self, animations):
        self.animations = animations
        self.cycles = 0
        self.frozen = False
        self.reset()

    def reset(self):
        self.anim_index = 0
        self.frame = 0
        self.repeat = 0
        self.timer = 0.0

    @property
    def current(self):
        return self.animations[self.anim_index]

    def update(self, dt):
        """시간을 dt 초만큼 진행시킨다."""
        if self.frozen:
            return

        self.timer += dt

        while self.timer >= FRAME_DURATION:
            self.timer -= FRAME_DURATION
            self.frame += 1

            if self.frame >= self.current.count:
                self.frame = 0
                self.repeat += 1

                # 5회 반복을 마쳤으면 1회 더 재생한 뒤 다음 애니메이션으로.
                if self.repeat >= REPEAT_COUNT + 1:
                    self.repeat = 0
                    self._advance()

    def _advance(self):
        """다음 애니메이션으로 넘어간다. 끝이면 처음부터 반복."""
        self.anim_index = (self.anim_index + 1) % len(self.animations)
        if self.anim_index == 0:
            self.cycles += 1

    def skip_next(self):
        """바로 다음 애니메이션으로 건너뛴다."""
        self.frame = 0
        self.repeat = 0
        self.timer = 0.0
        self._advance()

    def toggle_pause(self):
        """재생/일시정지를 전환한다. 반환값은 새 상태."""
        self.frozen = not self.frozen
        return self.frozen

    def step_frame(self, delta):
        """한 프레임만 앞으로/뒤로 이동한다."""
        self.frame += delta
        if self.frame >= self.current.count:
            self.frame = 0
            self.repeat += 1
            if self.repeat >= REPEAT_COUNT + 1:
                self.repeat = 0
                self._advance()
        elif self.frame < 0:
            self.frame = self.current.count - 1
            self.repeat -= 1
            if self.repeat < 0:
                self.repeat = REPEAT_COUNT
                self.anim_index = (self.anim_index - 1) % len(self.animations)
        self.timer = 0.0

    def status_text(self):
        """상태 표시 문자열."""
        return (f"{self.current.name}   "
                f"{self.repeat + 1}/{REPEAT_COUNT + 1} 회   "
                f"frame {self.frame + 1}/{self.current.count}   "
                f"cycle {self.cycles}")


def main():
    meta = load_meta()
    sheet = pico2d.load_image(os.path.join(BASE_DIR, meta["image"]))
    print(f"시트 {meta['image']}  애니메이션 {meta['animation_count']}개 "
          f"프레임 {meta['total_frames']}개")

    pico2d.open_canvas(CANVAS_W, CANVAS_H)
    set_window_title("LEC09 Animation Viewer")

    animations = load_animations(meta, sheet)
    player = Player(animations)
    fonts = (
        find_font(44),
        find_font(20),
        find_font(16),
    )

    state = {
        "flip": False,
        "paused": False,
        "step_mode": False,
        "scale": 1.0,
    }

    running = True
    last_time = pico2d.get_time()
    while running:
        if not handle_events(player, state):
            break

        now = pico2d.get_time()
        player.update(now - last_time)
        last_time = now

        pico2d.clear_canvas()
        draw_background()
        draw_frame(player.current, player.frame, state["flip"],
                   state["scale"])
        draw_strip(player.current, player.frame)
        draw_ui(fonts, player, state["paused"], state["step_mode"],
                state["scale"])
        pico2d.update_canvas()

    pico2d.close_canvas()


if __name__ == "__main__":
    main()
