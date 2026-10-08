"""Strict, byte-preserving reader for the DS3 MSB3 subset used by this tool.

Layout reference: SoulsFormats MSB3 (https://github.com/soulsmods/SoulsFormatsNEXT).
No offset is inferred from a name or a byte-pattern search.
"""
from dataclasses import dataclass
import struct
import zlib


class FormatError(ValueError):
    pass


def unpack_dcx(data):
    if data[:4] == b'MSB ':
        return data, None
    if len(data) < 76 or data[:4] != b'DCX\0':
        raise FormatError('지원하지 않는 파일입니다 (DS3 DFLT DCX 필요).')
    # DCA position is described by the DCP offset and its length, not by
    # the header's 0x14 field (that field is NOT an absolute payload offset).
    dcs, dcp = struct.unpack_from('>II', data, 8)
    if data[dcs:dcs+4] != b'DCS\0' or data[dcp:dcp+8] != b'DCP\0DFLT':
        raise FormatError('DFLT 압축 형식만 지원합니다.')
    dca = dcp + struct.unpack_from('>I', data, dcp + 8)[0]
    if data[dca:dca+4] != b'DCA\0':
        raise FormatError('잘못된 DCX 압축 헤더입니다.')
    payload = dca + struct.unpack_from('>I', data, dca + 4)[0]
    raw_size, comp_size = struct.unpack_from('>II', data, dcs + 4)
    if payload + comp_size > len(data) or raw_size > 128 * 1024 * 1024:
        raise FormatError('DCX 크기 필드가 잘못되었습니다.')
    obj = zlib.decompressobj()
    raw = obj.decompress(data[payload:payload+comp_size], raw_size + 1)
    if len(raw) != raw_size or not obj.eof or obj.unconsumed_tail:
        raise FormatError('DCX 압축 해제 검증에 실패했습니다.')
    return raw, data[:payload]


def pack_dcx(raw, header):
    if header is None:
        return raw
    packed = zlib.compress(raw, 9)
    h = bytearray(header)
    dcs = struct.unpack_from('>I', h, 8)[0]
    struct.pack_into('>II', h, dcs + 4, len(raw), len(packed))
    return bytes(h) + packed


def value(raw, fmt, off):
    if off < 0 or off + struct.calcsize(fmt) > len(raw):
        raise FormatError('MSB 오프셋이 파일 범위를 벗어납니다.')
    return struct.unpack_from(fmt, raw, off)


def text16(raw, off):
    start = off
    for _ in range(2048):
        if value(raw, '<H', off)[0] == 0:
            return raw[start:off].decode('utf-16-le')
        off += 2
    raise FormatError('MSB 문자열이 너무 깁니다.')


def sections(raw):
    if raw[:16] != b'MSB \x01\0\0\0\x10\0\0\0\0\0\x01\xff':
        raise FormatError('지원하는 DS3 MSB3 헤더가 아닙니다.')
    result, seen, off = {}, set(), 16
    while off:
        if off in seen or len(seen) >= 16:
            raise FormatError('순환하는 MSB 섹션입니다.')
        seen.add(off)
        version, count, nameoff = value(raw, '<iiq', off)
        if count < 1 or count > 100000:
            raise FormatError('잘못된 MSB 엔트리 수입니다.')
        entries = value(raw, '<' + 'q'*(count-1), off+16)
        nextoff = value(raw, '<q', off+16+8*(count-1))[0]
        name = text16(raw, nameoff)
        if name in result:
            raise FormatError('중복 MSB 섹션입니다.')
        result[name] = (version, entries)
        off = nextoff
    return result


@dataclass(frozen=True)
class Enemy:
    model: str
    name: str
    offset: int
    entity: int
    groups: tuple
    talk: int
    npc: int
    think: int
    layer: int
    position: tuple


def enemies(raw):
    sec = sections(raw)
    mv, models = sec['MODEL_PARAM_ST']
    pv, parts = sec['PARTS_PARAM_ST']
    if mv != 3 or pv != 3:
        raise FormatError('MSB3 버전 3만 지원합니다.')
    model_names = [text16(raw, p + value(raw, '<q', p)[0]) for p in models]
    found = []
    for p in parts:
        if value(raw, '<I', p+8)[0] != 2:
            continue
        index = value(raw, '<i', p+16)[0]
        if not 0 <= index < len(model_names):
            raise FormatError('잘못된 적 모델 인덱스입니다.')
        entityoff, typeoff = value(raw, '<qq', p+176)
        if entityoff < 208 or typeoff < 208:
            raise FormatError('적 데이터 오프셋이 잘못되었습니다.')
        eid = value(raw, '<i', p+entityoff)[0]
        groups = value(raw, '<8i', p+entityoff+28)
        think, npc, talk = value(raw, '<3i', p+typeoff+8)
        position = value(raw, '<3f', p+32)
        layer = value(raw, '<I', p+72)[0]
        name = text16(raw, p + value(raw, '<q', p)[0])
        found.append(Enemy(model_names[index], name, p, eid, groups, talk,
                           npc, think, layer, position))
    return found


def suppress(raw, targets):
    """Remove placements from every ceremony and every backread group.

    Retain all part indices, model links, EntityIDs, groups and event data.
    This is not a kill and does not grant enemy loot or set death flags.
    """
    out = bytearray(raw)
    allowed = set()
    for e in targets:
        for off, length in ((e.offset+72, 4), (e.offset+140, 32)):
            out[off:off+length] = b'\0' * length
            allowed.update(range(off, off+length))
    actual = {i for i, (a, b) in enumerate(zip(raw, out)) if a != b}
    if len(out) != len(raw) or not actual <= allowed:
        raise FormatError('허용되지 않은 바이트가 변경되었습니다.')
    return bytes(out), len(actual)
