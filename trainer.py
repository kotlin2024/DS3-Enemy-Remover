"""Persisted selections and continuous reconciliation of freshly read enemies."""
from collections import Counter
import json
from pathlib import Path
import threading
import time
from memory import GameMemory, NotReady
from localization import EN_NAMES, EN_MAPS, translate

# Candidate flags from TGA No Hit/Attack/Move, No Update and Backread/Swap.
# Backread behavior and physical collision are NOT validated in-game yet.
MASKS = ((0,0xE0),(1,0x88))


class Controller:
    def __init__(self, home, resources, adapter=GameMemory, clock=time.monotonic):
        self.home, self.resources = Path(home),Path(resources)
        self.home.mkdir(parents=True,exist_ok=True)
        self.manifest = json.loads((self.resources/'placements.json').read_text('utf-8'))
        self.profiles = json.loads((self.resources/'versions.json').read_text('utf-8'))['profiles']
        self.adapter = adapter
        self.clock=clock
        self.ready_context=None
        self.ready_since=None
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.language = 'ko'
        self.removal_mode = 'all'
        self.mod_warning_ack = False
        settings_path = self.home/'settings.json'
        if settings_path.exists():
            settings = json.loads(settings_path.read_text('utf-8'))
            if settings.get('language') in ('ko','en'):
                self.language = settings['language']
            if settings.get('removal_mode') in ('all','placements'):
                self.removal_mode = settings['removal_mode']
        self.active = False
        self.experimental = False
        self.offline = False
        self.memory = None
        self.saved = {}
        self.context = None
        self.selection = set()
        self.status = '게임 실행을 기다리고 있습니다.'
        self.current = Counter()
        self.attempts = 0
        self.removal_complete=False
        self.target_count=0
        self.applied_count=0
        path = self.home/'selection.json'
        if path.exists():
            data = json.loads(path.read_text('utf-8'))
            self.selection = self.validate_selection(data.get('selection',[]))
        self.policy = {}
        for map_id, m in self.manifest['maps'].items():
            grouped = {}
            for p in m['placements']:
                grouped.setdefault((p['model'],p['entity']),[]).append(p['protected'])
            self.policy[map_id] = {key:not any(reasons) for key,reasons in grouped.items()}

    def validate_selection(self, values):
        if not isinstance(values,list) or len(values)>500 or any(not isinstance(v,str) for v in values):
            raise ValueError('잘못된 몬스터 선택입니다.')
        catalog = self.manifest['catalog']
        if any(v not in catalog or catalog[v]['category']=='보호 대상' for v in values):
            raise ValueError('보스/NPC 또는 미지원 종류가 포함되어 있습니다.')
        return set(values)

    def set_language(self, language):
        if language not in ('ko','en'):
            raise ValueError('Invalid language. Choose ko or en.')
        with self.lock:
            self.save_settings(language,self.removal_mode)
            self.language=language

    def save_settings(self, language, mode):
        path=self.home/'settings.json'
        temp=path.with_suffix('.tmp')
        temp.write_text(json.dumps({'language':language,'removal_mode':mode}),encoding='utf-8')
        temp.replace(path)

    def set_mode(self, mode):
        if mode not in ('all','placements'):
            raise ValueError('Invalid removal mode.')
        with self.lock:
            if mode == self.removal_mode: return
            self.pause()
            self.save_settings(self.language,mode)
            self.removal_mode=mode
            self.status='제거 방식을 변경했습니다. 몹 제거 시작을 눌러 주세요.'

    def warning_required(self):
        return bool(self.removal_mode=='all' and self.memory and
                    getattr(self.memory,'modded',False) and not self.mod_warning_ack)

    def select(self, values):
        selection = self.validate_selection(values)
        with self.lock:
            path = self.home/'selection.json'
            temp = path.with_suffix('.tmp')
            temp.write_text(json.dumps({'selection':sorted(selection)},ensure_ascii=False),encoding='utf-8')
            temp.replace(path)
            self.selection = selection
            self.removal_complete=False
            if self.active and self.experimental:
                self.status='몹 제거 중'

    def allowed(self, identity, context):
        row=self.manifest['catalog'].get(identity[1])
        if identity[0]==context[1] or not row or row['category']=='보호 대상': return False
        placement=self.policy.get(context[2],{}).get((identity[1],identity[2]))
        if placement is False: return False  # Keep known boss/NPC placements excluded.
        return self.removal_mode=='all' or placement is True

    def start(self, offline, experimental=False, mod_warning_ack=False):
        if offline is not True:
            raise ValueError('게임의 오프라인 설정을 확인해 주세요.')
        with self.lock:
            if experimental is True and self.warning_required():
                if mod_warning_ack is not True:
                    raise ValueError('모드 주의사항을 확인한 뒤 몹 제거를 시작해 주세요.')
                self.mod_warning_ack=True
            self.offline, self.experimental, self.active = True,experimental is True,True

    def pause(self):
        with self.lock:
            self.active = False
            self.restore()
            self.status='일시중지 · 가능한 개체를 복원했습니다.'
            self.removal_complete=False

    def restore_one(self, identity, original, context):
        if not self.memory.validate(identity,context):
            return
        address = identity[0]+self.memory.profile['flags_offset']
        for offset,mask in MASKS:
            if not self.memory.validate(identity,context):
                return
            current = self.memory.read(address+offset,1)[0]
            self.memory.write_byte(address+offset,(current & ~mask)|(original[offset]&mask))

    def restore(self):
        if self.memory and self.context:
            for identity, original in list(self.saved.items()):
                try:
                    self.restore_one(identity,original,self.context)
                except (OSError,ValueError,NotReady):
                    pass
        self.saved.clear()

    def tick(self):
        with self.lock:
            self.removal_complete=False
            self.target_count=0
            self.applied_count=0
            if self.memory and not self.memory.alive():
                self.memory.close()
                self.memory = None
                self.saved.clear()
                self.context = None
            if not self.memory:
                self.memory = self.adapter(self.profiles)
            if not self.memory.playable():
                self.restore()
                self.ready_context=None
                self.ready_since=None
                self.current.clear()
                self.status='로딩 중 · 몹 제거를 잠시 멈춥니다.'
                return
            context, identities = self.memory.snapshot()
            if context != self.context:
                self.saved.clear()  # Never write to objects from the previous map/lifetime.
                self.context = context
            self.current = Counter(i[1] for i in identities)
            live = set(identities)
            for identity in list(self.saved):
                if identity not in live:
                    del self.saved[identity]
            if not self.active:
                self.status = '연결됨 · 읽기 전용 대기' + (' · 모드 로더 감지(연결 허용)' if getattr(self.memory,'modded',False) else '')
                return
            if not self.memory.profile['verified_in_game'] and not self.experimental:
                self.status = '읽기 전용 진단 중 · 몹 제거 사용을 체크하면 선택한 몬스터를 제거합니다.'
                return
            if not self.offline:
                raise NotReady('오프라인 확인이 필요합니다.')
            if self.warning_required():
                self.active=False
                self.restore()
                self.status='모드가 감지되었습니다. 몹 제거 시작을 눌러 주의사항을 확인해 주세요.'
                return
            if self.ready_context!=context:
                self.ready_context=context
                self.ready_since=self.clock()
            if self.clock()-self.ready_since<1.0:
                self.status='로딩 완료 확인 중 · 잠시 후 몹 제거를 재개합니다.'
                return
            self.memory.writable()
            self.target_count=sum(i[1] in self.selection and self.allowed(i,context) for i in identities)
            for identity in identities:
                should_remove = identity[1] in self.selection and self.allowed(identity,context)
                if not should_remove:
                    if identity in self.saved:
                        self.restore_one(identity,self.saved.pop(identity),context)
                    continue
                if not self.memory.validate(identity,context):
                    continue
                address = identity[0]+self.memory.profile['flags_offset']
                current = self.memory.read(address,2)
                self.saved.setdefault(identity,current)
                changed = False
                for offset,mask in MASKS:
                    if not self.memory.playable():
                        self.restore()
                        self.ready_context=None
                        self.ready_since=None
                        self.status='로딩 중 · 몹 제거를 잠시 멈춥니다.'
                        return
                    if not self.memory.validate(identity,context):
                        break
                    value = self.memory.read(address+offset,1)[0]
                    if value & mask != mask:
                        self.memory.write_byte(address+offset,value|mask)
                        changed = True
                if changed:
                    self.attempts += 1
                if self.memory.validate(identity,context):
                    applied=self.memory.read(address,2)
                    if all(applied[offset]&mask==mask for offset,mask in MASKS):
                        self.applied_count+=1
            if not self.memory.playable():
                self.restore()
                self.ready_context=None
                self.ready_since=None
                self.status='로딩 중 · 몹 제거를 잠시 멈춥니다.'
                return
            self.removal_complete=self.target_count>0 and self.applied_count==self.target_count
            if self.removal_complete:
                self.status='제거 완료'
            elif self.target_count:
                self.status='몹 제거 중'
            else:
                self.status='현재 불러온 제거 대상 없음' if self.selection else '제거할 몬스터를 선택하세요.'

    def run(self):
        while not self.stop.wait(0.15):
            try:
                self.tick()
            except (OSError,ValueError,NotReady,StopIteration) as error:
                with self.lock:
                    self.status = str(error) or '게임 상태 변경을 기다리고 있습니다.'
                    self.current.clear()
                    # If a write failed halfway through, restore only objects
                    # that still pass all identity/context checks.
                    self.restore()
                    # Loading/unknown pointers never cause writes to cached objects.
                    self.saved.clear()
                    self.context = None
                    self.ready_context=None
                    self.ready_since=None
                    if self.memory and not self.memory.alive():
                        self.memory.close()
                        self.memory = None
        with self.lock:
            self.restore()
            if self.memory:
                self.memory.close()

    def state(self):
        with self.lock:
            return dict(selection=sorted(self.selection), active=self.active, language=self.language,
                        removal_enabled=self.experimental or bool(self.memory and self.memory.profile['verified_in_game']),
                        removal_mode=self.removal_mode,mod_detected=bool(self.memory and getattr(self.memory,'modded',False)),
                        mod_warning_required=self.warning_required(),
                        status=translate(self.status,self.language), map=self.context[2] if self.context else '',
                        loaded=dict(self.current), attempts=self.attempts,
                        removal_complete=self.removal_complete,target_count=self.target_count,applied_count=self.applied_count,
                        verified=False, rows=[dict(r,name=EN_NAMES[r['id']] if self.language=='en' else r['name'],
                            name_ko=r['name'],name_en=EN_NAMES[r['id']]) for r in self.manifest['catalog'].values()],
                        maps=[dict(id=k,name=EN_MAPS.get(k,k) if self.language=='en' else v['name'],models=dict(Counter(p['model'] for p in v['placements'])))
                              for k,v in self.manifest['maps'].items() if v['placements']])
