"""Local trainer UI. Unverified memory writes require explicit test mode."""
import argparse
import ctypes
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import sys
import threading
from trainer import Controller
from localization import translate
display_language='ko'


def main():
    global display_language
    for name,mode in [('stdin','r'),('stdout','w'),('stderr','w')]:
        if getattr(sys,name,None) is None:
            setattr(sys,name,open(os.devnull,mode,encoding='utf-8'))
    parser = argparse.ArgumentParser()
    parser.add_argument('--headless',action='store_true',help='진단용: 전용 창 없이 로컬 서버만 실행')
    parser.add_argument('--no-browser',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--desktop-smoke',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--port',type=int,default=0)
    parser.add_argument('--home')
    args = parser.parse_args()
    root = Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
    home = Path(args.home).resolve() if args.home else (Path(sys.executable).parent if getattr(sys,'frozen',False) else root/'runtime')
    if (home/'settings.json').exists():
        settings=json.loads((home/'settings.json').read_text('utf-8'))
        display_language='en' if settings.get('language')=='en' else 'ko'
    # One owner per selection file and memory session.
    from ctypes import wintypes
    k = ctypes.WinDLL('kernel32',use_last_error=True)
    k.CreateMutexW.argtypes = [ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
    k.CreateMutexW.restype = wintypes.HANDLE
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    mutex_name='Local\\DS3EnemyTrainer-single-game-owner'
    if args.desktop_smoke:
        mutex_name+='-desktop-smoke'
    mutex = k.CreateMutexW(None,False,mutex_name)
    if not mutex:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:
        k.CloseHandle(mutex)
        raise RuntimeError('다른 DS3 Enemy Trainer가 이미 실행 중입니다. 이전 버전의 화면에서 프로그램 종료를 누르거나 전용 창을 닫은 뒤 다시 실행해 주세요. 브라우저 탭을 닫는 것만으로는 이전 버전이 종료되지 않습니다.')
    if args.desktop_smoke:
        from memory import NotReady
        def no_game_adapter(profiles):
            raise NotReady('전용 창 진단 · 게임 메모리는 변경하지 않습니다.')
        controller = Controller(home,root,no_game_adapter)
    else:
        controller = Controller(home,root)
    token = secrets.token_urlsafe(32)
    worker = threading.Thread(target=controller.run,daemon=True)
    worker.start()
    headless=args.headless or args.no_browser
    host=None

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):
            pass

        def respond(self,code,data,kind='application/json; charset=utf-8'):
            if isinstance(data,dict) and 'error' in data:
                data=dict(data,error=translate(data['error'],controller.language))
            blob = json.dumps(data,ensure_ascii=False).encode('utf-8') if isinstance(data,dict) else data
            self.send_response(code)
            for key,value in {'Content-Type':kind,'Content-Length':str(len(blob)),
                              'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
                              'X-Frame-Options':'DENY','Referrer-Policy':'no-referrer',
                              'Content-Security-Policy':"default-src 'self'; img-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'"}.items():
                self.send_header(key,value)
            self.end_headers()
            self.wfile.write(blob)

        def valid(self,token_required=False):
            return (self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'
                    and (not token_required or self.headers.get('X-Trainer-Token') == token))

        def do_GET(self):
            if not self.valid():
                return self.respond(403,{'error':'허용되지 않은 요청입니다.'})
            if self.path == '/':
                page = (root/'ui.html').read_text('utf-8').replace('__TOKEN__',token)
                return self.respond(200,page.encode('utf-8'),'text/html; charset=utf-8')
            if self.path == '/assets/mascots.png':
                return self.respond(200,(root/'assets'/'mascots.png').read_bytes(),'image/png')
            if self.path in ('/i18n.js','/ui.js'):
                return self.respond(200,(root/self.path[1:]).read_bytes(),'text/javascript; charset=utf-8')
            if self.path == '/api/state' and self.valid(True):
                return self.respond(200,controller.state())
            return self.respond(404,{'error':'없는 경로입니다.'})

        def do_POST(self):
            if not self.valid(True) or self.headers.get('Origin') not in (None,f'http://127.0.0.1:{self.server.server_port}'):
                return self.respond(403,{'error':'허용되지 않은 요청입니다.'})
            try:
                length = int(self.headers.get('Content-Length','0'))
                if not 0<length<32768 or self.headers.get('Content-Type','').split(';')[0] != 'application/json':
                    raise ValueError('잘못된 요청 형식입니다.')
                body = json.loads(self.rfile.read(length))
                if not isinstance(body,dict):
                    raise ValueError('잘못된 요청입니다.')
                if self.path == '/api/selection':
                    controller.select(body.get('selection'))
                elif self.path == '/api/language':
                    controller.set_language(body.get('language'))
                elif self.path == '/api/mode':
                    controller.set_mode(body.get('mode'))
                elif self.path == '/api/start':
                    controller.start(body.get('offline'),body.get('experimental'),body.get('mod_warning_ack'))
                elif self.path == '/api/pause':
                    controller.pause()
                elif self.path == '/api/quit':
                    controller.pause()
                    self.respond(200,{'ok':True})
                    threading.Thread(target=host.close if host else self.server.shutdown,daemon=True).start()
                    return
                else:
                    return self.respond(404,{'error':'없는 경로입니다.'})
                return self.respond(200,{'ok':True})
            except (OSError,ValueError,RuntimeError) as error:
                return self.respond(400,{'error':translate(str(error),controller.language)})

    server = ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    server.daemon_threads = False
    url = f'http://127.0.0.1:{server.server_port}'
    (home/'session.json').write_text(json.dumps({'url':url}),encoding='utf-8')
    print(url,flush=True)
    server_thread=None
    try:
        if headless:
            server.serve_forever(poll_interval=0.2)
        else:
            from desktop import DesktopHost
            host=DesktopHost(controller,home,args.desktop_smoke)
            server_thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':0.2},daemon=True)
            server_thread.start()
            host.open(url)
    finally:
        controller.stop.set()
        worker.join()
        if server_thread:
            server.shutdown()
            server_thread.join()
        server.server_close()
        k.CloseHandle(mutex)
        if args.desktop_smoke:
            (home/'desktop-lifecycle.json').write_text(json.dumps({
                'window_closed':bool(host and host.closed.is_set()),
                'worker_stopped':not worker.is_alive(),
                'server_stopped':not server_thread or not server_thread.is_alive(),
            }),encoding='utf-8')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        if getattr(sys,'frozen',False):
            import traceback
            (Path(sys.executable).parent/'startup-error.log').write_text(traceback.format_exc(),encoding='utf-8')
            if '--desktop-smoke' in sys.argv:
                sys.exit(1)
            ctypes.windll.user32.MessageBoxW(0,translate(str(error),display_language),'DS3 Enemy Trainer',0x10)
        else:
            raise
