"""Read-only DS3 EMEVD boss references, including initialized event parameters.

Layout reference: SoulsFormats EMEVD; command reference: soulsmods DS3 EMEDF.
No game script is executed or distributed by this module.
"""
import struct
from msb3 import unpack_dcx


def read_events(blob):
    raw = unpack_dcx(blob)[0] if blob[:4] == b'DCX\0' else blob
    if raw[:8] != b'EVD\0\0\xff\x01\0' or struct.unpack_from('<i', raw, 8)[0] != 0xCD:
        raise ValueError('Unsupported EMEVD header')
    def get(fmt, pos):
        if pos < 0 or pos + struct.calcsize(fmt) > len(raw):
            raise ValueError('EMEVD offset out of bounds')
        return struct.unpack_from(fmt, raw, pos)
    header = get('<16q', 16)
    count, events_at, instructions_at, parameters_at, args_at = header[0], header[1], header[3], header[9], header[13]
    if not 0 <= count <= 100000: raise ValueError('EMEVD event count')
    events = {}
    for index in range(count):
        eid, n, off, pn, poff, _, _ = get('<5q2i', events_at + index * 48)
        if not 0 <= n <= 100000 or not 0 <= pn <= 100000: raise ValueError('EMEVD count')
        instructions = []
        for i in range(n):
            bank, cmd, size, arg_off, _ = get('<iiqqq', instructions_at + off + i * 32)
            if size < 0 or size > 65536: raise ValueError('EMEVD arguments')
            pos = args_at + arg_off
            if size and (pos < 0 or pos + size > len(raw)): raise ValueError('EMEVD argument offset')
            instructions.append((bank, cmd, raw[pos:pos+size] if size else b''))
        parameters = [get('<qqqii', parameters_at + poff + p * 32) for p in range(pn)]
        events[eid] = instructions, parameters
    return events


def boss_references(events, common=None):
    """Conservatively collect every boss health-bar/defeat entity reference.

    Parameterless events are inspected even if conditional; event calls resolve
    substituted argument bytes recursively. This does not simulate event logic.
    """
    common = common or {}
    result, seen = {}, set()
    def visit(eid, payload, library, depth=0):
        key = (id(library), eid, payload)
        if key in seen or depth > 32 or eid not in library: return
        seen.add(key)
        instructions, parameters = library[eid]
        for index, (bank, cmd, original) in enumerate(instructions):
            args = bytearray(original)
            valid = True
            for ins, target, source, size, _ in parameters:
                if ins != index: continue
                if target < 0 or source < 0 or size <= 0 or target+size > len(args) or source+size > len(payload):
                    valid = False
                    break
                args[target:target+size] = payload[source:source+size]
            if not valid: continue
            if bank == 2003 and cmd == 11 and len(args) >= 16:
                entity, name = struct.unpack_from('<i', args, 4)[0], struct.unpack_from('<i', args, 12)[0]
                if entity > 0: result.setdefault(entity, set()).add(name)
            elif bank == 2003 and cmd in (12, 15) and len(args) >= 4:
                entity = struct.unpack_from('<i', args)[0]
                if entity > 0: result.setdefault(entity, set())
            elif bank == 2000 and cmd == 0 and len(args) >= 8:
                called = struct.unpack_from('<I', args, 4)[0]
                visit(called, bytes(args[8:]), library if called in library else common, depth+1)
            elif bank == 2000 and cmd == 6 and len(args) >= 4:
                visit(struct.unpack_from('<I', args)[0], bytes(args[4:]), common, depth+1)
    for eid, (_, params) in events.items():
        if not params: visit(eid, b'', events)
    return result
