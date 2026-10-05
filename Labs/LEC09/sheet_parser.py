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
import zlib

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


def collect_idat(data):
    """IDAT 청크 페이로드를 이어 붙여 압축 스트림을 만든다.

    PNG 규격상 하나의 이미지가 여러 IDAT 청크로 나뉠 수 있으므로
    순서대로 모두 모아야 한다.
    """
    buffer = bytearray()
    for chunk_type, payload in iter_chunks(data):
        if chunk_type == b"IDAT":
            buffer += payload
    if not buffer:
        raise PngError("IDAT 청크가 없습니다.")
    return bytes(buffer)


def decompress_idat(data, expected_size):
    """IDAT 스트림을 zlib 으로 풀어 스캔라인 바이트열을 얻는다.

    expected_size 는 (필터바이트 1 + width * 4) * height 이며,
    실제로 나온 길이와 비교해 잘린 파일을 조기에 감지한다.
    """
    try:
        raw = zlib.decompress(collect_idat(data))
    except zlib.error as exc:
        raise PngError(f"zlib 해제 실패: {exc}") from exc

    if len(raw) != expected_size:
        raise PngError(
            f"해제된 크기가 기대와 다릅니다: {len(raw)} != {expected_size}"
        )
    return raw


def _paeth(a, b, c):
    """Paeth 예측기: 왼쪽/위/왼쪽위 픽셀로부터 가장 가까운 값을 추정."""
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def unfilter(raw, width, height):
    """필터가 적용된 스캔라인들을 원본 픽셀열로 되돌린다.

    PNG 는 각 행 맨 앞에 필터 종류(0~4)를 기록하고,
    나머지는 위/왼쪽 픽셀과의 차이만 저장한다.
    아래는 규격의 각 필터를 되돌리는 역연산이다.

        0 None      : 원본 그대로
        1 Sub       : 왼쪽 픽셀을 더함
        2 Up        : 위쪽 픽셀을 더함
        3 Average   : (왼쪽 + 위) // 2 를 더함
        4 Paeth     : 왼쪽/위/왼위 중 추정값을 더함
    """
    stride = width * 4          # RGBA = 한 픽셀 4바이트
    out = bytearray(height * stride)
    previous = bytearray(stride)
    position = 0

    for y in range(height):
        filter_type = raw[position]
        position += 1
        line = bytearray(raw[position:position + stride])
        position += stride

        if filter_type == 0:
            pass
        elif filter_type == 1:
            for i in range(4, stride):
                line[i] = (line[i] + line[i - 4]) & 0xFF
        elif filter_type == 2:
            for i in range(stride):
                line[i] = (line[i] + previous[i]) & 0xFF
        elif filter_type == 3:
            for i in range(stride):
                left = line[i - 4] if i >= 4 else 0
                line[i] = (line[i] + ((left + previous[i]) >> 1)) & 0xFF
        elif filter_type == 4:
            for i in range(stride):
                left = line[i - 4] if i >= 4 else 0
                up = previous[i]
                up_left = previous[i - 4] if i >= 4 else 0
                line[i] = (line[i] + _paeth(left, up, up_left)) & 0xFF
        else:
            raise PngError(f"알 수 없는 필터 종류: {filter_type}")

        out[y * stride:(y + 1) * stride] = line
        previous = line

    return out


def load_pixels(path):
    """PNG 파일을 RGBA 픽셀 바이트열로 읽는다."""
    with open(path, "rb") as handle:
        data = handle.read()

    header = read_header(data)
    width, height = header["width"], header["height"]
    raw = decompress_idat(data, (width * 4 + 1) * height)
    return width, height, unfilter(raw, width, height)


def alpha_mask(width, height, pixels):
    """RGBA 픽셀열에서 알파 마스크를 뽑는다.

    스프라이트 시트는 배경이 완전 투명(alpha 0)이라
    '무엇이 그려져 있는지'는 알파 값만 보면 알 수 있다.
    마스크는 1차원 bytearray 로, 값이 0 아니면 그림이 있는 칸이다.
    """
    mask = bytearray(width * height)
    for index in range(width * height):
        mask[index] = 1 if pixels[index * 4 + 3] > 0 else 0
    return mask


def empty_runs(flags):
    """flags(True == 빈 칸)에서 연속된 빈 구간을 뽑아낸다.

    빈틈이 연속되는 곳이 곧 스프라이트 사이의 경계이므로,
    '빈 구간'이 아니라 '그림이 있는 연속 구간'을 프레임 후보로 쓴다.
    여기서는 상태 배열을 만들기 위한 기반 함수로만 사용한다.
    """
    spans = []
    start = None
    for index, is_empty in enumerate(flags):
        if is_empty and start is None:
            start = index
        elif not is_empty and start is not None:
            spans.append((start, index - 1))
            start = None
    if start is not None:
        spans.append((start, len(flags) - 1))
    return spans


def occupied_spans(flags):
    """flags 에서 그림이 있는 연속 구간을 (시작, 끝, 길이) 로 반환."""
    spans = []
    start = None
    for index, is_empty in enumerate(flags):
        if not is_empty and start is None:
            start = index
        elif is_empty and start is not None:
            spans.append((start, index - 1, index - start))
            start = None
    if start is not None:
        spans.append((start, len(flags) - 1, len(flags) - start))
    return spans


def row_bands(width, height, mask):
    """세로 방향으로 그림이 몰린 구간(행 밴드)을 찾는다.

    세로로 완전히 비어 있는 행을 경계로 삼으면
    스프라이트가 나란히 놓인 줄 단위로 나눌 수 있다.
    """
    row_empty = [
        all(mask[y * width + x] == 0 for x in range(width))
        for y in range(height)
    ]
    return occupied_spans(row_empty)


def column_spans(width, height, mask):
    """가로 방향으로 그림이 몰린 구간(열 밴드)을 찾는다."""
    col_empty = [
        all(mask[y * width + x] == 0 for y in range(height))
        for x in range(width)
    ]
    return occupied_spans(col_empty)


def connected_boxes(width, height, mask, region=None):
    """알파 마스크에서 상하좌우로 이어진 영역(연결 요소)을 찾는다.

    스프라이트 하나가 몸통/다리/머리처럼 여러 조각으로
    나뉘어 그려질 수 있으므로, 각 조각의 경계 상자가 아니라
    '같은 프레임에 속하는 조각 묶음'을 얻어야 한다.

    region 이 주어지면 (x0, y0, x1, y1) 범위 안에서만 탐색한다.
    반환: list of dict(x0, y0, x1, y1, width, height, area)
    """
    x_start, y_start, x_end, y_end = region or (0, 0, width - 1, height - 1)
    visited = set()
    boxes = []
    stack = []

    for y in range(y_start, y_end + 1):
        for x in range(x_start, x_end + 1):
            if mask[y * width + x] == 0 or (x, y) in visited:
                continue

            visited.add((x, y))
            stack.append((x, y))
            x0 = x1 = x
            y0 = y1 = y
            area = 0

            while stack:
                cx, cy = stack.pop()
                area += 1
                if cx < x0: x0 = cx
                if cx > x1: x1 = cx
                if cy < y0: y0 = cy
                if cy > y1: y1 = cy

                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if not (x_start <= nx <= x_end and y_start <= ny <= y_end):
                        continue
                    if mask[ny * width + nx] == 0 or (nx, ny) in visited:
                        continue
                    visited.add((nx, ny))
                    stack.append((nx, ny))

            boxes.append({
                "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                "width": x1 - x0 + 1,
                "height": y1 - y0 + 1,
                "area": area,
            })

    return boxes
