"""External Windows memory adapter; no injected code or game file writes."""
import ctypes as c
from ctypes import wintypes as w
import hashlib
from pathlib import Path
import struct
import configparser
import time
from probe import kernel, entries, ProcessEntry, ModuleEntry, read
from mod_detection import process_modengine_config, modengine2_variant


class NotReady(RuntimeError):
    pass


class GameMemory:
    hash_cache = {}
    def __init__(self, profiles):
        self.k = kernel()
        self.handle = None
        candidates = [p for p in entries(self.k,2,0,ProcessEntry,'Process32FirstW','Process32NextW')
                      if p.name.lower() == 'darksoulsiii.exe']
        if not candidates:
            raise NotReady('게임 실행을 기다리고 있습니다.')
        if len(candidates) != 1:
            raise NotReady('게임이 여러 개 실행되어 연결하지 않았습니다.')
        self.pid = candidates[0].pid
        modules = list(entries(self.k,0x18,self.pid,ModuleEntry,'Module32FirstW','Module32NextW'))
        main = next(m for m in modules if m.name.lower() == 'darksoulsiii.exe')
        self.path, self.base = Path(main.path), main.base
        stat = self.path.stat()
        key = (str(self.path),stat.st_size,stat.st_mtime_ns)
        digest = self.hash_cache.get(key)
        if digest is None:
            digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
            self.hash_cache[key] = digest
        self.profile = next((p for p in profiles if p['sha256'] == digest),None)
        if not self.profile:
            raise NotReady('지원 지문과 다른 게임 실행 파일입니다. 메모리를 변경하지 않습니다.')
        # Loader presence is informational, not a blanket compatibility veto.
        proxies = {'dinput8.dll','dxgi.dll','winmm.dll','version.dll'}
        self.modded = any(m.name.lower()=='modengine2.dll' or (m.name.lower() in proxies and Path(m.path).parent == self.path.parent)
                          for m in modules)
        self.modded |= any((self.path.parent/n).exists() for n in ('modengine.ini','HoodiePatcher.dll'))
        self.game_variant = self.detect_variant(modules)
        self.variant_checked_at = time.monotonic()
        self.handle = self.k.OpenProcess(0x1010,False,self.pid)
        if not self.handle:
            raise c.WinError(c.get_last_error())
        self.k.WriteProcessMemory.argtypes = [w.HANDLE,c.c_void_p,c.c_void_p,c.c_size_t,c.POINTER(c.c_size_t)]
        self.k.WriteProcessMemory.restype = w.BOOL
        self.k.GetExitCodeProcess.argtypes = [w.HANDLE,c.POINTER(w.DWORD)]
        self.k.GetExitCodeProcess.restype = w.BOOL

    def detect_variant(self, modules):
        if any(m.name.lower()=='modengine2.dll' for m in modules):
            # The launcher passes the selected TOML path to the game process.
            # A leftover legacy INI must not override this evidence.
            return modengine2_variant(process_modengine_config(self.k,self.pid))
        # Installed folders alone do not tell us which mod is active. Inspect
        # the loader's configured override only when its proxy is loaded.
        loaded = any(m.name.lower() in ('dinput8.dll','dxgi.dll','winmm.dll','version.dll')
                     and Path(m.path).parent == self.path.parent for m in modules)
        if not loaded: return 'vanilla'
        config = configparser.ConfigParser(interpolation=None,strict=False)
        try:
            config.read(self.path.parent/'modengine.ini',encoding='utf-8-sig')
            for section in config.sections():
                if config.get(section,'useModOverrideDirectory',fallback='0').strip() != '1': continue
                folder = config.get(section,'modOverrideDirectory',fallback='').lower()
                if 'convergence' in folder: return 'convergence'
                if 'cinders' in folder: return 'cinders'
        except (OSError,configparser.Error,UnicodeError): pass
        return 'unknown'

    def refresh_variant(self, force=False):
        # Steam can start the executable before its mod proxy finishes loading.
        # Re-read module/config evidence instead of retaining the startup result.
        now = time.monotonic()
        if not force and now-self.variant_checked_at < 2.0:
            return
        self.variant_checked_at = now
        try:
            modules = list(entries(self.k,0x18,self.pid,ModuleEntry,'Module32FirstW','Module32NextW'))
        except OSError:
            return  # Retain the last result if the process is transitioning.
        self.game_variant = self.detect_variant(modules)
        proxies = {'dinput8.dll','dxgi.dll','winmm.dll','version.dll'}
        self.modded = any(m.name.lower()=='modengine2.dll' or (m.name.lower() in proxies and Path(m.path).parent == self.path.parent)
                          for m in modules)
        self.modded |= any((self.path.parent/n).exists() for n in ('modengine.ini','HoodiePatcher.dll'))

    def close(self):
        if self.handle:
            self.k.CloseHandle(self.handle)
            self.handle = None

    def alive(self):
        code = w.DWORD()
        return bool(self.handle and self.k.GetExitCodeProcess(self.handle,c.byref(code)) and code.value == 259)

    def read(self, address, size):
        return read(self.k,self.handle,address,size)

    def ptr(self, address):
        return struct.unpack('<Q',self.read(address,8))[0]

    def integer(self, address):
        return struct.unpack('<i',self.read(address,4))[0]

    def writable(self):
        new_handle = self.k.OpenProcess(0x1038,False,self.pid)
        if not new_handle:
            raise c.WinError(c.get_last_error())
        self.k.CloseHandle(self.handle)
        self.handle = new_handle

    def write_byte(self, address, value):
        data = c.c_ubyte(value)
        count = c.c_size_t()
        if not self.k.WriteProcessMemory(self.handle,address,c.byref(data),1,c.byref(count)) or count.value != 1:
            raise c.WinError(c.get_last_error())

    def context(self):
        world = self.ptr(self.base + self.profile['world_rva'])
        if not world:
            raise NotReady('타이틀 또는 로딩 화면입니다.')
        player = self.ptr(world+0x80)
        if not player:
            raise NotReady('캐릭터 로드를 기다리고 있습니다.')
        first = self.ptr(player+0x1AC8)
        second = self.ptr(first+0x18)
        block = struct.unpack('<I',self.read(second+0x4E8,4))[0]
        parts = [(block >> n) & 255 for n in (24,16,8,0)]
        map_id = 'm' + '_'.join(f'{p:02d}' for p in parts)
        return world,player,map_id

    def playable(self):
        # Read-only loading/fade checks resolved for the fingerprinted executable.
        # Pointer presence alone does not mean enemy initialization is complete.
        if self.integer(self.base+self.profile['loading_rva']) != 0:
            return False
        fade=self.ptr(self.base+self.profile['fade_rva'])
        if not fade: return False
        system=self.ptr(fade+8)
        return bool(system and self.integer(system+0x2ec)==0)

    def soul_snapshot(self):
        if not self.alive() or not self.playable():
            raise NotReady('소울 변경은 캐릭터 로딩이 끝난 뒤 사용할 수 있습니다.')
        context = self.context()
        manager = self.ptr(self.base+self.profile['game_data_rva'])
        data = self.ptr(manager+self.profile['player_game_data_offset'])
        address = data+self.profile['souls_offset']
        value = self.integer(address)
        if not 0 <= value <= 999999999:
            raise NotReady('소울 정보를 확인할 수 없습니다.')
        if context != self.context() or not self.playable():
            raise NotReady('소울 변경은 캐릭터 로딩이 끝난 뒤 사용할 수 있습니다.')
        return (context,manager,data,address),value

    def set_souls(self, value):
        if type(value) is not int or not 0 <= value <= 999999999:
            raise ValueError('소울은 0부터 999999999까지의 정수로 입력해 주세요.')
        identity,_ = self.soul_snapshot()
        self.writable()
        fresh,_ = self.soul_snapshot()
        if fresh != identity or not self.playable():
            raise NotReady('소울 변경은 캐릭터 로딩이 끝난 뒤 사용할 수 있습니다.')
        data = c.c_int32(value)
        count = c.c_size_t()
        if not self.k.WriteProcessMemory(self.handle,identity[3],c.byref(data),4,c.byref(count)) or count.value != 4:
            raise c.WinError(c.get_last_error())
        verified,current = self.soul_snapshot()
        if verified != identity or current != value:
            raise NotReady('소울 적용을 확인하지 못했습니다. 현재 소울을 확인해 주세요.')
        return current

    def identity(self, address):
        modules = self.ptr(address+self.profile['modules_offset'])
        data = self.ptr(modules+0x18)
        model = self.read(data+0x130,10).decode('utf-16-le')
        if len(model) != 5 or model[0] != 'c' or not model[1:].isdigit():
            raise NotReady('적 모델 식별자가 예상 구조와 다릅니다.')
        entity = self.integer(address+0x1A1C)
        return address,model,entity,data

    def snapshot(self):
        context = self.context()
        found = {}
        for offset in self.profile['enumeration_offsets']:
            table = self.ptr(context[0]+offset)
            if not table:
                continue
            count, array = self.integer(table),self.ptr(table+8)
            if not 0 <= count <= 4096 or (count and not array):
                raise NotReady('적 목록 범위가 예상 구조와 다릅니다.')
            # Reference table uses indices 1..count.
            for i in range(1,count+1):
                address = self.ptr(array+i*self.profile['list_stride'])
                if not address or address == context[1]:
                    continue
                try:
                    found[address] = self.identity(address)
                except (OSError,ValueError,UnicodeError,NotReady):
                    continue
        if context != self.context():
            raise NotReady('지역이 바뀌고 있습니다.')
        return context, list(found.values())

    def validate(self, identity, context):
        return self.alive() and self.context() == context and self.identity(identity[0]) == identity
