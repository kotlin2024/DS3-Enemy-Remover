"""Read-only DS3 process probe. No writes, injection or game file changes.

Initial development diagnostic, NOT a working enemy-removal trainer.
"""
import ctypes as c
from ctypes import wintypes as w
import json
import os
import struct


class ProcessEntry(c.Structure):
    _fields_ = [('size', w.DWORD), ('usage', w.DWORD), ('pid', w.DWORD),
                ('heap', c.c_size_t), ('module', w.DWORD), ('threads', w.DWORD),
                ('parent', w.DWORD), ('priority', w.LONG), ('flags', w.DWORD),
                ('name', w.WCHAR * 260)]


class ModuleEntry(c.Structure):
    _fields_ = [('size', w.DWORD), ('module_id', w.DWORD), ('pid', w.DWORD),
                ('global_usage', w.DWORD), ('process_usage', w.DWORD),
                ('base', c.c_void_p), ('length', w.DWORD), ('module', w.HMODULE),
                ('name', w.WCHAR * 256), ('path', w.WCHAR * 260)]


def kernel():
    if os.name != 'nt' or c.sizeof(c.c_void_p) != 8:
        raise RuntimeError('64비트 Windows/Python이 필요합니다.')
    k = c.WinDLL('kernel32', use_last_error=True)
    specs = {
        'CreateToolhelp32Snapshot': ([w.DWORD, w.DWORD], w.HANDLE),
        'Process32FirstW': ([w.HANDLE, c.POINTER(ProcessEntry)], w.BOOL),
        'Process32NextW': ([w.HANDLE, c.POINTER(ProcessEntry)], w.BOOL),
        'Module32FirstW': ([w.HANDLE, c.POINTER(ModuleEntry)], w.BOOL),
        'Module32NextW': ([w.HANDLE, c.POINTER(ModuleEntry)], w.BOOL),
        'OpenProcess': ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
        'CloseHandle': ([w.HANDLE], w.BOOL),
        'ReadProcessMemory': ([w.HANDLE, c.c_void_p, c.c_void_p, c.c_size_t,
                               c.POINTER(c.c_size_t)], w.BOOL),
    }
    for name, (args, result) in specs.items():
        getattr(k, name).argtypes = args
        getattr(k, name).restype = result
    return k


def entries(k, flags, pid, entry_type, first, following):
    snapshot = k.CreateToolhelp32Snapshot(flags, pid)
    if snapshot == c.c_void_p(-1).value:
        raise c.WinError(c.get_last_error())
    try:
        entry = entry_type()
        entry.size = c.sizeof(entry)
        ok = getattr(k, first)(snapshot, c.byref(entry))
        while ok:
            yield entry_type.from_buffer_copy(entry)
            ok = getattr(k, following)(snapshot, c.byref(entry))
        error = c.get_last_error()
        if error not in (0, 18):
            raise c.WinError(error)
    finally:
        k.CloseHandle(snapshot)


def read(k, handle, address, size):
    if address < 0x10000 or size < 1 or size > 4096:
        raise ValueError('잘못된 읽기 범위입니다.')
    buffer = c.create_string_buffer(size)
    count = c.c_size_t()
    if not k.ReadProcessMemory(handle, address, buffer, size, c.byref(count)):
        raise c.WinError(c.get_last_error())
    if count.value != size:
        raise RuntimeError('게임 상태 변경으로 읽기를 완료하지 못했습니다.')
    return buffer.raw


def probe():
    k = kernel()
    processes = [p for p in entries(k, 2, 0, ProcessEntry, 'Process32FirstW',
                                    'Process32NextW')
                 if p.name.lower() == 'darksoulsiii.exe']
    if not processes:
        return {'state': 'game_not_running', 'message': '다크소울3가 실행되어 있지 않습니다.',
                'read_only': True, 'removal_available': False}
    if len(processes) != 1:
        raise RuntimeError('게임 프로세스가 여러 개여서 연결하지 않았습니다.')
    pid = processes[0].pid
    modules = [m for m in entries(k, 0x18, pid, ModuleEntry, 'Module32FirstW',
                                  'Module32NextW')
               if m.name.lower() == 'darksoulsiii.exe']
    if len(modules) != 1:
        raise RuntimeError('게임 실행 모듈을 확인할 수 없습니다.')
    handle = k.OpenProcess(0x1010, False, pid)  # QUERY_LIMITED_INFORMATION | VM_READ
    if not handle:
        raise c.WinError(c.get_last_error())
    try:
        module = modules[0]
        if read(k, handle, module.base, 2) != b'MZ':
            raise RuntimeError('게임 실행 모듈이 예상 구조와 다릅니다.')
        pe_offset = struct.unpack('<I', read(k, handle, module.base + 0x3C, 4))[0]
        if pe_offset < 0x40 or pe_offset > 4096:
            raise RuntimeError('실행 파일 헤더 범위가 예상 구조와 다릅니다.')
        header = read(k, handle, module.base + pe_offset, 24)
        if header[:4] != b'PE\0\0' or struct.unpack_from('<H', header, 4)[0] != 0x8664:
            raise RuntimeError('64비트 게임 실행 모듈이 아닙니다.')
        return {'state': 'attached_read_only', 'pid': pid, 'path': module.path,
                'module_base': hex(module.base), 'module_size': module.length,
                'pe_timestamp': struct.unpack_from('<I', header, 8)[0],
                'read_only': True, 'removal_available': False,
                'message': '읽기 전용 연결 확인. 몬스터 제거 기능은 아직 개발 중입니다.'}
    finally:
        k.CloseHandle(handle)


if __name__ == '__main__':
    try:
        result = probe()
    except (OSError, RuntimeError, ValueError) as error:
        result = {'state': 'error', 'message': str(error), 'read_only': True,
                  'removal_available': False}
    print(json.dumps(result, ensure_ascii=False, indent=2))
