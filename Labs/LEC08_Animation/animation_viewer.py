"""
애니메이션 뷰어 (LEC08 과제)
============================
스프라이트 시트 4종(걷기 / 뛰기 / 점프 / 공격)을 화면 중앙에서 재생한다.

- 각 애니메이션은 5회 반복한 뒤 1초 정지하고, 다음 애니메이션으로 넘어간다.
- 모든 애니메이션을 순서대로 무한 반복한다.
- 프레임마다 크기가 다른(가변) 스프라이트 시트를 사용한다.
- 프레임 안에 기록된 앵커(발밑 지점)를 기준으로 정렬하므로
  프레임 크기가 달라도 캐릭터가 흔들리지 않는다.

실행:  python animation_viewer.py
"""

import json
import os

import pico2d

# ---------------------------------------------------------------
# 상수
# ---------------------------------------------------------------
CANVAS_W, CANVAS_H = 800, 600

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
META_PATH = os.path.join(BASE_DIR, "sheet_meta.json")

REPEAT_COUNT = 5          # 각 애니메이션 반복 횟수
PAUSE_SECONDS = 1.0       # 반복 후 정지 시간
FRAME_DURATION = 1.0 / 30 # 프레임 표시 시간 (고정 스텝)

# 캐릭터 표시 크기 (화면 세로의 60% -> 절반 이상 조건 충족)
CHAR_HEIGHT = 360
CHAR_SHEET_UNITS = 208.0    # 시트에서 캐릭터 1unit 이 차지하는 픽셀 수
BASE_SCALE = CHAR_HEIGHT / CHAR_SHEET_UNITS
SCALE_STEP = 0.2             # UP/DOWN 키 조정 단위
MIN_SCALE = 0.5
MAX_SCALE = 4.0
SCALE = BASE_SCALE           # 현재 배율 (실행 중 변경 가능)

# 캐릭터 발밑을 놓을 화면 좌표 (캐릭터가 화면 중앙에 오도록 계산)
FOOT_X = CANVAS_W / 2
FOOT_Y = CANVAS_H / 2 - CHAR_HEIGHT / 2

# 색상
BG = (26, 28, 36, 255)
GROUND = (48, 52, 68, 255)
GROUND_LINE = (96, 106, 134, 255)
LABEL = (235, 238, 245, 255)
SUB_LABEL = (150, 158, 178, 255)

KEY_HELP = "SPACE pause | N next | R restart | LEFT/RIGHT flip | UP/DOWN size | 0 reset | ESC quit"

# 라벨용 폰트 (없는 경우 None -> 라벨만 생략)
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\malgun.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
]


def find_font():
    """사용 가능한 TrueType 폰트 경로를 찾는다."""
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


class Animation:
    """애니메이션 하나: 시트 이미지 + 프레임 정보."""

    def __init__(self, data):
        self.name = data["name"]
        self.image = pico2d.load_image(os.path.join(BASE_DIR, data["image"]))
        self.fps = data["fps"]
        self.frames = data["frames"]
        self.sheet_h = self.image.h

    def count(self):
        return len(self.frames)

    def frame_rect(self, i):
        """프레임 i 의 (left, bottom, width, height) 를 반환.

        이 pico2d 버전의 clip_composite_draw 는 bottom 이 '이미지 아랫면으로부터
        의 거리' 를 받는다. 시트 좌표는 top 이므로 변환이 필요하다.
        """
        f = self.frames[i % self.count()]
        bottom = self.sheet_h - f["top"] - f["height"]
        return f["left"], bottom, f["width"], f["height"]

    def anchor(self, i):
        """프레임 i 의 발밑 앵커 (프레임 좌상단 기준 픽셀 좌표)."""
        f = self.frames[i % self.count()]
        return f["anchor_x"], f["anchor_y"]


def load_animations():
    """메타데이터를 읽어 Animation 리스트를 만든다.

    시트가 아직 생성되지 않았다면 안내 메시지와 함께 종료한다.
    """
    if not os.path.exists(META_PATH):
        print("=" * 58)
        print("스프라이트 시트를 찾을 수 없습니다: sheet_meta.json")
        print("먼저 아래 명령을 실행하세요:")
        print("    python make_sprite_sheet.py")
        print("=" * 58)
        raise SystemExit(1)

    with open(META_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    anims = data.get("animations", [])
    if not anims:
        print("sheet_meta.json 에 애니메이션이 없습니다.")
        raise SystemExit(1)

    animations = []
    for a in anims:
        img_path = os.path.join(BASE_DIR, a["image"])
        if not os.path.exists(img_path):
            print(f"시트 이미지 없음: {a['image']} "
                  f"(python make_sprite_sheet.py 실행 필요)")
            raise SystemExit(1)
        animations.append(Animation(a))
    return animations


class Player:
    """재생 상태 관리기.

    동작 순서: 각 애니메이션을 REPEAT_COUNT 번 반복 -> 1초 정지 -> 다음으로.
    마지막 애니메이션까지 마치면 다시 첫 번째로 돌아간다(무한 반복).
    """

    def __init__(self, animations):
        self.anims = animations
        self.frozen = False      # 사용자가 일시정지했는지
        self.reset()

    def reset(self):
        self.anim_index = 0
        self.repeat = 0            # 현재 애니메이션을 반복한 횟수
        self.frame = 0             # 현재 애니메이션 내 프레임 인덱스
        self.timer = 0.0           # 누적 시간
        self.pausing = False       # 정지 구간인지 여부

    def toggle_freeze(self):
        """SPACE: 재생/일시정지 전환."""
        self.frozen = not self.frozen

    def skip_to_next(self):
        """N: 다음 애니메이션으로 건너뛴다."""
        self.pausing = False
        self.repeat = 0
        self.frame = 0
        self.timer = 0.0
        self.anim_index = (self.anim_index + 1) % len(self.anims)

    @property
    def current(self):
        return self.anims[self.anim_index]

    def update(self, dt):
        """시간을(dt 초만큼) 진행시킨다."""
        if self.frozen:
            return

        self.timer += dt

        if self.pausing:
            if self.timer >= PAUSE_SECONDS:
                self.timer = 0.0
                self.pausing = False
                self.repeat = 0
                self.frame = 0
                self.anim_index = (self.anim_index + 1) % len(self.anims)
            return

        # 프레임 수가 달라도 동일 속도로 재생되도록 고정 스텝 사용
        while self.timer >= FRAME_DURATION:
            self.timer -= FRAME_DURATION
            self.frame += 1
            if self.frame >= self.current.count():
                self.frame = 0
                self.repeat += 1
                if self.repeat >= REPEAT_COUNT:
                    self.repeat = 0
                    self.pausing = True
                    self.timer = 0.0
                    break

    def status_text(self):
        """하단 상태 표시용 문자열."""
        if self.frozen:
            return "PAUSED (SPACE)"
        if self.pausing:
            return "PAUSE"
        return (f"{self.repeat + 1}/{REPEAT_COUNT}  "
                f"frame {self.frame + 1}/{self.current.count()}")


def draw_background():
    """배경과 바닥을 그린다.

    (캐릭터 그림자는 스프라이트 시트에 이미 포함되어 있다.)
    """
    pico2d.draw_rectangle(0, 0, CANVAS_W, CANVAS_H, *BG, True)
    pico2d.draw_rectangle(0, 0, CANVAS_W, FOOT_Y, *GROUND, True)
    # 바닥 위 경계선
    pico2d.draw_rectangle(0, FOOT_Y - 2, CANVAS_W, FOOT_Y, *GROUND_LINE, True)


def draw_character(anim, frame_index, facing_right=True, scale=None):
    """발밑 앵커가 (FOOT_X, FOOT_Y) 에 오도록 캐릭터를 확대해 그린다.

    프레임마다 원본 크기가 다르므로, 배율을 고정한 채 앵커를 기준으로
    화면 좌표를 계산해야 캐릭터 크기가 프레임마다 달라지지 않는다.

    facing_right=False 이면 좌우 반전('h')해 반대 방향을 보게 한다.
    """
    scale = SCALE if scale is None else scale
    left, bottom, w, h = anim.frame_rect(frame_index)
    ax, ay = anim.anchor(frame_index)

    dw = w * scale
    dh = h * scale

    # clip_composite_draw 의 (x, y) 는 목적지 사각형의 중심.
    # 발밑(앵커)이 (FOOT_X, FOOT_Y) 에 정확히 오도록 중심을 역산한다.
    cx = FOOT_X + dw / 2 - ax * scale
    cy = FOOT_Y - dh / 2 + ay * scale

    anim.image.clip_composite_draw(
        left, bottom, w, h,
        0, '' if facing_right else 'h',
        cx, cy,
        dw, dh,
    )


def handle_events(player, state):
    """키보드/창 이벤트를 처리한다. 종료 요청 시 False 반환.

    state 는 뷰어 설정(방향, 크기 배율, 디버그 표시)을 담은 dict 이며
    함수 안에서 직접 수정된다.
    """
    for e in pico2d.get_events():
        if e.type == pico2d.SDL_QUIT:
            return False
        if e.type != pico2d.SDL_KEYDOWN:
            continue

        if e.key == pico2d.SDLK_ESCAPE:
            return False
        elif e.key == pico2d.SDLK_SPACE:
            player.toggle_freeze()
        elif e.key == pico2d.SDLK_n:
            player.skip_to_next()
        elif e.key == pico2d.SDLK_r:
            player.reset()
        elif e.key == pico2d.SDLK_RIGHT:
            state["facing_right"] = True
        elif e.key == pico2d.SDLK_LEFT:
            state["facing_right"] = False
        elif e.key == pico2d.SDLK_UP:
            state["scale"] = min(state["scale"] + SCALE_STEP, MAX_SCALE)
        elif e.key == pico2d.SDLK_DOWN:
            state["scale"] = max(state["scale"] - SCALE_STEP, MIN_SCALE)
        elif e.key == pico2d.SDLK_0:
            state["scale"] = BASE_SCALE
    return True


def main():
    pico2d.open_canvas(CANVAS_W, CANVAS_H)
    pico2d.SDL_SetWindowTitle("LEC08 Animation Viewer")
    animations = load_animations()
    player = Player(animations)

    title_font = info_font = None
    font_path = find_font()
    if font_path:
        try:
            title_font = pico2d.load_font(font_path, 44)
            info_font = pico2d.load_font(font_path, 20)
        except Exception as exc:      # 폰트 로드 실패해도 재생은 계속
            print("font load failed:", exc)
            title_font = info_font = None

    running = True
    last_time = pico2d.get_time()
    state = {"facing_right": True, "scale": BASE_SCALE}

    while running:
        if not handle_events(player, state):
            break

        now = pico2d.get_time()
        dt = now - last_time
        last_time = now
        player.update(dt)

        draw_background()
        draw_character(player.current, player.frame,
                       state["facing_right"], state["scale"])

        # 현재 애니메이션 이름 / 진행 상태 표시
        anim = player.current
        if title_font:
            title_font.draw(CANVAS_W / 2, CANVAS_H - 60, anim.name.upper(), LABEL[:3])
            info_font.draw(CANVAS_W / 2, CANVAS_H - 26, player.status_text(), SUB_LABEL[:3])
            info_font.draw(CANVAS_W / 2, 30, KEY_HELP, SUB_LABEL[:3])

        pico2d.update_canvas()

    pico2d.close_canvas()


if __name__ == '__main__':
    main()
