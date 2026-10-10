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
                    # UI/API exercise against an isolated, in-memory character.
                    # This adapter never opens or writes a real process.
                    class SoulPreview:
                        profile={'verified_in_game':False}
                        game_variant='vanilla'
                        modded=False
                        balance=12345
                        def alive(self):return True
                        def playable(self):return True
                        def close(self):pass
                        def refresh_variant(self,force=False):pass
                        def snapshot(self):return (0x100000,0x110000,'m40_00_00_00'),[]
                        def soul_snapshot(self):return (((0x100000,0x110000,'m40_00_00_00'),0x400000,0x410000,0x410074),self.balance)
                        def set_souls(self,value):self.balance=value;return value
                    preview=SoulPreview()
                    with self.controller.lock:
                        self.controller.memory=preview
                        self.controller.experimental=False
                    deadline=time.monotonic()+15
                    while time.monotonic()<deadline:
                        soul_ready=self.window.evaluate_js("({ready:state.souls_ready,disabled:document.getElementById('soulsApply').disabled,label:document.querySelector('#soulsPanel h2').textContent})")
                        if soul_ready['ready']:break
                        time.sleep(.1)
                    if not soul_ready['ready'] or not soul_ready['disabled'] or soul_ready['label']!='Set souls':
                        raise RuntimeError('Soul card did not require offline confirmation.')
                    self.window.evaluate_js("document.getElementById('soulsOffline').checked=true;document.getElementById('soulsOffline').dispatchEvent(new Event('change'));document.getElementById('soulsValue').value='1e6';document.getElementById('soulsApply').click();void 0")
                    invalid=self.window.evaluate_js("document.getElementById('soulsStatus').textContent")
                    if invalid!='Enter a whole number from 0 to 999999999.' or preview.balance!=12345:
                        raise RuntimeError('Invalid soul input was accepted.')
                    self.window.evaluate_js("document.getElementById('soulsValue').value='1000000';document.getElementById('soulsApply').click();void 0")
                    deadline=time.monotonic()+15
                    while time.monotonic()<deadline:
                        soul_applied=self.window.evaluate_js("({value:document.getElementById('soulsCurrent').textContent,message:document.getElementById('soulsStatus').textContent,active:state.active,busy:soulsBusy,width:document.getElementById('soulsPanel').getBoundingClientRect().width,position:document.getElementById('soulsPanel').previousElementSibling.contains(document.getElementById('start'))})")
                        if not soul_applied['busy'] and soul_applied['value']=='1,000,000':break
                        time.sleep(.1)
                    if preview.balance!=1000000 or soul_applied['active'] or not soul_applied['position'] or soul_applied['width']<280 or '1,000,000' not in soul_applied['message']:
                        raise RuntimeError('Soul UI/API apply or panel placement failed.')
                    with self.controller.lock:
                        self.controller.memory=None
                        self.controller.context=None
                        self.controller.souls_current=None
                        self.controller.souls_ready=False
                        self.controller.souls_context=None
                        self.controller.souls_since=None
                    result['souls_simulation']=dict(offline_gate=soul_ready,invalid_input=invalid,applied=soul_applied,real_game_written=False)
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
                    tabs=[]
                    for variant, model in [('convergence','c1103'),('cinders','c7610'),('vanilla','c2140')]:
                        self.window.evaluate_js(f"document.querySelector('[data-variant={variant}]').click();void 0")
                        deadline=time.monotonic()+15
                        while time.monotonic()<deadline:
                            tab=self.window.evaluate_js("({variant:state.game_variant,ready:!variantBusy,active:state.active,tabCount:document.querySelectorAll('#profileTabs button').length})")
                            if tab['variant']==variant and tab['ready']:break
                            time.sleep(0.1)
                        if tab['variant']!=variant or tab['active'] or tab['tabCount']!=3:
                            raise RuntimeError('Game tabs did not switch and pause.')
                        self.window.evaluate_js(f"document.getElementById('search').value='{model}';document.getElementById('search').dispatchEvent(new Event('input'));void 0")
                        card=self.window.evaluate_js(f"({{present:!!document.querySelector('[data-id={model}]'),enabled:!document.querySelector('[data-id={model}]')?.disabled}})")
                        if not card['present'] or not card['enabled']:
                            raise RuntimeError('Mod enemy card not selectable.')
                        self.window.evaluate_js(f"document.querySelector('[data-id={model}]').click();void 0")
                        deadline=time.monotonic()+15
                        while time.monotonic()<deadline:
                            saved=self.window.evaluate_js(f"({{selected:selected.has('{model}'),saving:saveStatusKey==='saving'}})")
                            if saved['selected'] and not saved['saving']:break
                            time.sleep(0.1)
                        if not saved['selected'] or saved['saving']:raise RuntimeError('Tab selection did not save.')
                        artwork=None
                        if variant!='vanilla':
                            self.window.evaluate_js(f"window.__modArt=new Image();window.__modArt.src='/assets/mascots_{variant}.png';void 0")
                            deadline=time.monotonic()+10
                            while time.monotonic()<deadline:
                                artwork=self.window.evaluate_js("({width:window.__modArt.naturalWidth,height:window.__modArt.naturalHeight,background:getComputedStyle(document.querySelector('#grid .sprite')).backgroundImage,size:getComputedStyle(document.querySelector('#grid .sprite')).backgroundSize,placeholder:!!document.querySelector('#grid .placeholder')})")
                                if artwork and artwork['width']>0:break
                                time.sleep(0.1)
                            rows=7 if variant=='convergence' else 6
                            if not artwork or artwork['width']*rows!=artwork['height']*4 or variant not in artwork['background'] or artwork['size']!=f'400% {rows*100}%' or artwork['placeholder']:
                                raise RuntimeError('Additional enemy artwork did not load or map correctly.')
                        tabs.append(dict(variant=variant,card=card,selection=saved,artwork=artwork))
                    stored=json.loads((self.home/'selection.json').read_text('utf-8'))['selections']
                    if stored['convergence']!=['c1103'] or stored['cinders']!=['c7610'] or stored['vanilla']!=['c2140']:
                        raise RuntimeError('Tab selections were not stored independently.')
                    result['game_tabs']=tabs
                    from mod_detection import modengine2_variant
                    loader_config=self.home/'loader-smoke.toml'
                    loader_config.write_text('[extension.mod_loader]\nmods=[{enabled=true,name="Cinders",path="Cinders"},{enabled=false,name="Convergence",path="The Convergence"}]\n',encoding='utf-8')
                    if modengine2_variant(loader_config)!='cinders':
                        raise RuntimeError('Packaged Mod Engine 2 config detection failed.')
                    result['modengine2_config']='cinders'

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
