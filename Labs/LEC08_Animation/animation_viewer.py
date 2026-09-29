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

# 캐릭터 표시 크기 (화면 세로의 약 2/3 -> 절반 이상 조건 충족)
CHAR_HEIGHT = 400
CHAR_WIDTH_AT_UNITS = 208.0  # 시트에서 캐릭터 1unit 이 차지하는 픽셀 수
SCALE = CHAR_HEIGHT / CHAR_WIDTH_AT_UNITS

# 캐릭터 발밑을 놓을 화면 좌표 (캐릭터가 화면 중앙에 오도록 계산)
FOOT_X = CANVAS_W / 2
FOOT_Y = CANVAS_H / 2 - CHAR_HEIGHT / 2

# 색상
BG = (26, 28, 36, 255)
GROUND = (48, 52, 68, 255)
LABEL = (235, 238, 245, 255)
SUB_LABEL = (150, 158, 178, 255)


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
    """메타데이터를 읽어 Animation 리스트를 만든다."""
    with open(META_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Animation(a) for a in data["animations"]]


class Player:
    """재생 상태 관리기.

    동작 순서: 각 애니메이션을 REPEAT_COUNT 번 반복 -> 1초 정지 -> 다음으로.
    마지막 애니메이션까지 마치면 다시 첫 번째로 돌아간다(무한 반복).
    """

    def __init__(self, animations):
        self.anims = animations
        self.reset()

    def reset(self):
        self.anim_index = 0
        self.repeat = 0            # 현재 애니메이션을 반복한 횟수
        self.frame = 0             # 현재 애니메이션 내 프레임 인덱스
        self.timer = 0.0           # 누적 시간
        self.pausing = False       # 정지 구간인지 여부

    @property
    def current(self):
        return self.anims[self.anim_index]

    def update(self, dt):
        """시간을(dt 초만큼) 진행시킨다."""
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
        if self.pausing:
            return "PAUSE"
        return f"{self.repeat + 1}/{REPEAT_COUNT}  frame {self.frame + 1}/{self.current.count()}"
