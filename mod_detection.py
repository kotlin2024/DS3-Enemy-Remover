"""Read-only loader evidence. Never infer an active mod from installed folders."""
import ctypes as c
from ctypes import wintypes as w
from pathlib import Path
import struct
from probe import read


def process_modengine_config(kernel, pid):
    """Read only MODENGINE_CONFIG from a 64-bit process environment, not our own."""
    handle=kernel.OpenProcess(0x0410,False,pid)
    if not handle:return None
    try:
        query=c.WinDLL('ntdll',use_last_error=True).NtQueryInformationProcess
        query.argtypes=[w.HANDLE,w.ULONG,c.c_void_p,w.ULONG,c.POINTER(w.ULONG)]
        query.restype=c.c_long
        info=(c.c_void_p*6)()
        size=w.ULONG()
        if query(handle,0,c.byref(info),c.sizeof(info),c.byref(size))<0 or not info[1]:return None
        parameters=struct.unpack('<Q',read(kernel,handle,info[1]+0x20,8))[0]
        environment=struct.unpack('<Q',read(kernel,handle,parameters+0x80,8))[0]
        data=bytearray()
        for offset in range(0,131072,256):
            data.extend(read(kernel,handle,environment+offset,256))
            # Environment terminators are UTF-16 code units, not arbitrary bytes.
            for index in range(max(0,len(data)-258),len(data)-3,2):
                if data[index:index+4]==b'\0\0\0\0':
                    for entry in data[:index].decode('utf-16-le').split('\0'):
                        key,sep,value=entry.partition('=')
                        if sep and key.upper()=='MODENGINE_CONFIG':return value or None
                    return None
    except (OSError,ValueError,UnicodeError):return None
    finally:kernel.CloseHandle(handle)
    return None


def modengine2_variant(config_path):
    if not config_path:return 'unknown'
    try:
        try:import tomllib
        except ImportError:import tomli as tomllib
        path=Path(config_path)
        if not path.is_absolute() or path.stat().st_size>1024*1024:return 'unknown'
        config=tomllib.loads(path.read_text('utf-8-sig'))
        loader=config.get('extension',{}).get('mod_loader',{})
        if loader.get('enabled',True) is not True:return 'unknown'
        variants=set()
        for mod in loader.get('mods',[]):
            if mod.get('enabled',True) is not True:continue
            label=(str(mod.get('name',''))+' '+str(mod.get('path',''))).lower()
            if 'convergence' in label:variants.add('convergence')
            if 'cinders' in label:variants.add('cinders')
        return next(iter(variants)) if len(variants)==1 else 'unknown'
    except (OSError,ValueError,TypeError,AttributeError,ImportError):return 'unknown'
