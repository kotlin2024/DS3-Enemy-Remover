"""Embedded WebView2 host; owns the native window and its lifetime."""
import json
from pathlib import Path
import threading
import time


def require_runtime():
    import winreg
    runtime_id='{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
    paths=[(winreg.HKEY_CURRENT_USER,rf'SOFTWARE\Microsoft\EdgeUpdate\Clients\{runtime_id}'),
           (winreg.HKEY_LOCAL_MACHINE,rf'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{runtime_id}')]
    for hive,path in paths:
        try:
            with winreg.OpenKey(hive,path) as key:
                version,_=winreg.QueryValueEx(key,'pv')
            if int(str(version).split('.')[0])>=86:
                return
        except (OSError,ValueError):
            pass
    raise RuntimeError('전용 창을 표시하려면 Microsoft Edge WebView2 Runtime이 필요합니다. README의 공식 설치 안내를 확인해 주세요.')


class DesktopHost:
    def __init__(self, controller, home, smoke=False):
        self.controller=controller
        self.home=Path(home)
        self.smoke=smoke
        self.window=None
        self.closed=threading.Event()
        self.smoke_error=None

    def on_closed(self):
        # No address writes on the GUI thread. Worker exits and restores in finally.
        self.controller.stop.set()
        self.closed.set()

    def close(self):
        if self.window:
            self.window.destroy()

    def open(self,url):
        try:
            require_runtime()
        except RuntimeError as error:
            from localization import translate
            raise RuntimeError(translate(str(error),self.controller.language)) from error
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('HJP.DS3EnemyRemover')
        import webview
        webview.settings['ALLOW_FILE_URLS']=False
        webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER']=False
        self.window=webview.create_window('DS3 Enemy Trainer',url,
                                         width=1240,height=880,min_size=(850,650),
                                         background_color='#F6F5EE',hidden=self.smoke)
        self.window.events.closed+=self.on_closed
        if self.smoke:
            def inspect_loaded():
                try:
                    from webview.platforms import winforms
                    if winforms.renderer!='edgechromium':
                        raise RuntimeError('WebView2 대신 다른 렌더러가 선택됐습니다.')
                    deadline=time.monotonic()+30
                    result=None
                    while time.monotonic()<deadline:
                        result=self.window.evaluate_js("({title:document.title,cards:document.querySelectorAll('#grid .card').length,selected:document.getElementById('chosen').textContent,status:document.getElementById('status').textContent,stylesLoaded:[...document.styleSheets].some(s=>s.cssRules.length>0)})")
                        if result and result['cards']>0:
                            break
                        time.sleep(0.1)
                    if not result or result['cards']<1:
                        raise RuntimeError('전용 창에서 선택 화면이 로드되지 않았습니다.')
                    self.window.evaluate_js("window.__desktopSmokeImage=new Image();window.__desktopSmokeImage.src='/assets/mascots.png';void 0")
                    image=None
                    while time.monotonic()<deadline:
                        image=self.window.evaluate_js("({width:window.__desktopSmokeImage.naturalWidth,height:window.__desktopSmokeImage.naturalHeight})")
                        if image and image['width']>0:
                            break
                        time.sleep(0.1)
                    if not image or image['width']<1000 or image['height']!=image['width']:
                        raise RuntimeError('전용 창에서 몬스터 이미지가 로드되지 않았습니다.')
                    result['image']=image
                    self.window.evaluate_js("document.getElementById('language').value='en';document.getElementById('language').dispatchEvent(new Event('change'));void 0")
                    deadline=time.monotonic()+20
                    english=None
                    while time.monotonic()<deadline:
                        english=self.window.evaluate_js("({lang:document.documentElement.lang,start:document.getElementById('start').textContent,area:[...document.getElementById('map').options].some(o=>o.textContent==='Cathedral of the Deep'),cards:document.querySelectorAll('#grid .card').length})")
                        if english['lang']=='en' and english['start']=='Start enemy removal': break
                        time.sleep(0.1)
                    if not english or english['lang']!='en' or not english['area'] or english['cards']<1:
                        raise RuntimeError('English language switch did not render.')
                    self.window.evaluate_js("document.getElementById('modePlacements').checked=true;document.getElementById('modePlacements').dispatchEvent(new Event('change'));void 0")
                    deadline=time.monotonic()+20
                    while time.monotonic()<deadline:
                        mode=self.window.evaluate_js("({value:state.removal_mode,paused:!state.active,description:document.querySelector('[data-i18n=modePlacementsDesc]').textContent,ready:!document.getElementById('modePlacements').disabled})")
                        if mode['value']=='placements' and mode['ready']: break
                        time.sleep(0.1)
                    if mode['value']!='placements' or not mode['paused'] or 'registered' not in mode['description']:
                        raise RuntimeError('Recognized-placement mode did not render or pause.')
                    self.window.evaluate_js("document.getElementById('modeAll').checked=true;document.getElementById('modeAll').dispatchEvent(new Event('change'));void 0")
                    deadline=time.monotonic()+20
                    while time.monotonic()<deadline:
                        all_mode=self.window.evaluate_js("({value:state.removal_mode,ready:!document.getElementById('modeAll').disabled})")
                        if all_mode['value']=='all' and all_mode['ready']: break
                        time.sleep(0.1)
                    if all_mode['value']!='all':raise RuntimeError('All-type mode did not render.')
                    self.window.evaluate_js("document.getElementById('modWarning').showModal();void 0")
                    warning=self.window.evaluate_js("({open:document.getElementById('modWarning').open,text:document.querySelector('[data-i18n=modWarningBody]').textContent})")
                    self.window.evaluate_js("document.getElementById('modCancel').click();void 0")
                    if not warning['open'] or 'boss or NPC' not in warning['text']:
                        raise RuntimeError('Bilingual mod warning did not render.')
                    result.update(placement_mode=mode,all_mode=all_mode,mod_warning=warning)
                    self.window.evaluate_js("document.getElementById('offline').checked=true;document.getElementById('experimental').checked=true;document.getElementById('start').click();void 0")
                    deadline=time.monotonic()+15
                    while time.monotonic()<deadline:
                        running=self.window.evaluate_js("({text:document.getElementById('start').textContent,disabled:document.getElementById('start').disabled})")
                        if running['text']=='Enemy removal running' and running['disabled']:break
                        time.sleep(0.1)
                    if running['text']!='Enemy removal running' or not running['disabled']:
                        raise RuntimeError('Start button did not reflect running state.')
                    self.window.evaluate_js("document.getElementById('pause').click();void 0")
                    deadline=time.monotonic()+15
                    while time.monotonic()<deadline:
                        paused=self.window.evaluate_js("({text:document.getElementById('start').textContent,disabled:document.getElementById('start').disabled})")
                        if paused['text']=='Start enemy removal' and not paused['disabled']:break
                        time.sleep(0.1)
                    if paused['text']!='Start enemy removal' or paused['disabled']:
                        raise RuntimeError('Start button did not reset after pausing.')
                    result.update(start_running=running,start_paused=paused)
                    self.window.evaluate_js("document.getElementById('search').value='Sewer Centipede';document.getElementById('search').dispatchEvent(new Event('input'));void 0")
                    match=self.window.evaluate_js("document.querySelector('#grid h3')?.textContent")
                    if match!='Sewer Centipede':
                        raise RuntimeError('English enemy search did not match the original name.')
                    self.window.evaluate_js("document.getElementById('language').value='ko';document.getElementById('language').dispatchEvent(new Event('change'));void 0")
                    deadline=time.monotonic()+20
                    while time.monotonic()<deadline:
                        korean=self.window.evaluate_js("({lang:document.documentElement.lang,start:document.getElementById('start').textContent})")
                        if korean['lang']=='ko' and korean['start']=='몹 제거 시작': break
                        time.sleep(0.1)
                    if korean['lang']!='ko' or korean['start']!='몹 제거 시작':
                        raise RuntimeError('Korean language switch did not render.')
                    result.update(english=english,english_search=match,korean=korean)
                    if self.window.native.Icon is None:
                        raise RuntimeError('Native window icon was not loaded.')
                    result.update(renderer=winforms.renderer,native_window=True,icon_loaded=True)
                    (self.home/'desktop-smoke.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
                except Exception as error:
                    self.smoke_error=error
                finally:
                    self.close()
            self.window.events.loaded+=inspect_loaded
        try:
            webview.start(gui='edgechromium',debug=False,private_mode=True,
                          storage_path=str(self.home/'webview-cache'),
                          icon=str(self.controller.resources/'assets'/'app-icon.ico'))
        finally:
            self.on_closed()
        if self.smoke_error:
            raise self.smoke_error
