"""
스프라이트 시트 파서 (LEC09 과제)
=================================
sonic-sprite.png 에서 애니메이션 시퀀스를 자동으로 찾아낸다.

시트는 399 x 525 크기의 자유 배치(free-form) 형태이므로
균일한 격자 대신 알파 채널의 빈틈을 기준으로 구조를 분석한다.

실행:  python sheet_parser.py
"""

import os
import struct

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SHEET_PATH = os.path.join(BASE_DIR, "sonic-sprite.png")
META_PATH = os.path.join(BASE_DIR, "sheet_meta.json")

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class PngError(Exception):
    """PNG 파일이 파싱 기대와 맞지 않을 때 발생한다."""


def iter_chunks(data):
    """PNG 바이트열을 (타입, 페이로드) 순서로 순회한다.

    첫 8바이트(서명)는 건너뛴 뒤 각 청크를
    [길이 4바이트][타입 4바이트][데이터][CRC 4바이트] 구조로 읽는다.
    """
    if data[:8] != PNG_SIGNATURE:
        raise PngError("PNG 서명이 아닙니다.")

    offset = len(PNG_SIGNATURE)
    while offset + 8 <= len(data):
        (length,) = struct.unpack(">I", data[offset:offset + 4])
        chunk_type = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + length]
        yield chunk_type, payload
        offset += 12 + length


def read_header(data):
    """IHDR 청크에서 이미지 헤더 정보를 읽는다.

    반환: dict(width, height, bit_depth, color_type, interlace)
    """
    for chunk_type, payload in iter_chunks(data):
        if chunk_type != b"IHDR":
            continue
        if len(payload) != 13:
            raise PngError(f"IHDR 길이가 13이 아닙니다: {len(payload)}")

        width, height, bit_depth, color_type, _comp, _filt, interlace = struct.unpack(
            ">IIBBBBB", payload
        )
        if bit_depth != 8:
            raise PngError(f"8비트 이미지만 지원합니다: {bit_depth}")
        if color_type != 6:
            raise PngError(f"RGBA(색상형식 6)만 지원합니다: {color_type}")
        if interlace != 0:
            raise PngError("인터레이스 이미지는 지원하지 않습니다.")

        return {
            "width": width,
            "height": height,
            "bit_depth": bit_depth,
            "color_type": color_type,
            "interlace": interlace,
        }

    raise PngError("IHDR 청크가 없습니다.")
