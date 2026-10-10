"""Lifecycle tests against an isolated fake process, never the real game."""
import json
from pathlib import Path
import tempfile
import unittest
from trainer import Controller, MASKS
from memory import GameMemory, NotReady
from types import SimpleNamespace
from unittest.mock import Mock, patch
from localization import EN_NAMES, translate

ROOT = Path(__file__).parent


class FakeMemory:
    profile = {'flags_offset':0x1EE8,'verified_in_game':False}
    def __init__(self,profiles):
        self.ctx = (0x100000,0x110000,'m33_00_00_00')
        self.ids = [(0x200000,'c2140',3300210,0x300000)]
        self.flags = {0x200000:bytearray([0x01,0x02])}
        self.writes = []
        self.loading = False
        self.running = True
        self.stale = False
    def snapshot(self):
        if self.loading: raise NotReady('loading')
        return self.ctx,self.ids.copy()
    def alive(self): return self.running
    def close(self): self.running=False
    def writable(self): pass
    def playable(self): return not self.loading
    def validate(self,i,ctx): return not self.stale and i in self.ids and ctx==self.ctx
    def read(self,address,n):
        for base,flags in self.flags.items():
            offset=address-base-self.profile['flags_offset']
            if 0<=offset<2: return bytes(flags[offset:offset+n])
        raise ValueError('invalid address')
    def write_byte(self,address,value):
        for base,flags in self.flags.items():
            offset=address-base-self.profile['flags_offset']
            if 0<=offset<2:
                flags[offset]=value
                self.writes.append((address,value))
                return
        raise ValueError('out of bounds')


class Tests(unittest.TestCase):
    def test_modengine2_reads_only_target_process_configuration(self):
        import os,subprocess,sys
        from probe import kernel
        from mod_detection import process_modengine_config
        config=str(Path(self.temp.name)/'신더 설정.toml')
        child=subprocess.Popen([sys.executable,'-c','import sys;print("ready",flush=True);sys.stdin.read()'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                               env=dict(os.environ,MODENGINE_CONFIG=config),creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            self.assertEqual(child.stdout.readline().strip(),b'ready')
            self.assertEqual(process_modengine_config(kernel(),child.pid),config)
        finally:
            child.stdin.close();child.wait(timeout=5)

    def test_modengine2_uses_active_config_not_stale_legacy_ini(self):
        from mod_detection import modengine2_variant
        folder=Path(self.temp.name)
        config=folder/'custom-config.toml'
        config.write_text('[extension.mod_loader]\nenabled=true\nmods=[{enabled=true,name="Cinders",path="Cinders"},{enabled=false,name="The Convergence",path="The Convergence"}]\n',encoding='utf-8')
        self.assertEqual(modengine2_variant(config),'cinders')
        (folder/'modengine.ini').write_text('[files]\nuseModOverrideDirectory=1\nmodOverrideDirectory="\\The Convergence"\n',encoding='utf-8')
        adapter=GameMemory.__new__(GameMemory)
        adapter.path=folder/'DarkSoulsIII.exe';adapter.k=Mock();adapter.pid=123
        modules=[SimpleNamespace(name='modengine2.dll',path=str(folder/'modengine2/bin/modengine2.dll'))]
        with patch('memory.process_modengine_config',return_value=str(config)):
            self.assertEqual(adapter.detect_variant(modules),'cinders')
        with patch('memory.process_modengine_config',return_value=None):
            self.assertEqual(adapter.detect_variant(modules),'unknown')
        self.assertEqual(adapter.detect_variant([]),'vanilla')

    def test_modengine2_unknown_disabled_malformed_and_conflicting_configs(self):
        from mod_detection import modengine2_variant
        config=Path(self.temp.name)/'custom-config.toml'
        for contents in ('[extension.mod_loader]\nenabled=false\nmods=[{name="Cinders",path="Cinders"}]',
                         '[extension.mod_loader]\nmods=[{enabled=false,name="Cinders",path="Cinders"}]',
                         '[extension.mod_loader]\nmods=[{name="Cinders",path="Cinders"},{name="Convergence",path="The Convergence"}]',
                         'not valid toml',
                         '[extension.mod_loader]\nmods=[{name="Other Mod",path="mod"}]'):
            config.write_text(contents,encoding='utf-8')
            self.assertEqual(modengine2_variant(config),'unknown')
        self.assertEqual(modengine2_variant(config.parent/'missing.toml'),'unknown')
        config.write_text('[extension.mod_loader]\nmods=[{name="The Convergence",path="mod"}]',encoding='utf-8')
        self.assertEqual(modengine2_variant(config),'convergence')

    def prepare_souls(self):
        self.soul_balance=12345
        self.soul_identity=(self.m.ctx,0x400000,0x410000,0x410074)
        def snapshot():
            if self.m.loading:raise NotReady('loading')
            return self.soul_identity,self.soul_balance
        def apply(value):self.soul_balance=value;return value
        self.m.soul_snapshot=Mock(side_effect=snapshot)
        self.m.set_souls=Mock(side_effect=apply)
        self.m.refresh_variant=Mock()
        self.c.tick();self.now+=2;self.c.tick()

    def test_souls_one_time_independent_of_enemy_removal(self):
        self.prepare_souls()
        self.assertFalse(self.c.active)
        self.assertFalse(self.c.experimental)
        selected=self.c.selection.copy()
        self.assertEqual(self.c.apply_souls(1000000,True),1000000)
        self.assertEqual(self.c.state()['souls_current'],1000000)
        self.assertEqual(self.c.selection,selected)
        self.assertEqual(self.m.writes,[])
        self.soul_balance=999900  # Spending souls must not be undone.
        self.c.tick()
        self.assertEqual(self.c.souls_current,999900)
        self.m.set_souls.assert_called_once_with(1000000)
        self.c.pause();self.assertEqual(self.soul_balance,999900)

    def test_souls_require_valid_integer_offline_and_stable_character(self):
        self.prepare_souls()
        for value in (True,None,'1000000',1.5,-1,1000000000):
            with self.assertRaises(ValueError):self.c.apply_souls(value,True)
        with self.assertRaises(ValueError):self.c.apply_souls(1000000,False)
        self.m.loading=True
        with self.assertRaises(NotReady):self.c.apply_souls(1000000,True)
        self.c.tick();self.assertFalse(self.c.souls_ready)
        self.assertIsNone(self.c.souls_current)
        self.m.loading=False;self.c.tick()
        with self.assertRaises(NotReady):self.c.apply_souls(1000000,True)
        self.now+=2;self.c.tick()
        self.soul_identity=(self.m.ctx,0x500000,0x510000,0x510074)
        with self.assertRaises(NotReady):self.c.apply_souls(1000000,True)
        self.m.set_souls.assert_not_called()

    def test_souls_mismatched_profile_blocks_write(self):
        self.prepare_souls();self.m.game_variant='cinders'
        with self.assertRaises(ValueError):self.c.apply_souls(1000000,True)
        self.m.set_souls.assert_not_called()

    def test_real_soul_adapter_writes_only_balance_and_rechecks_identity(self):
        import ctypes,struct
        adapter=GameMemory.__new__(GameMemory)
        adapter.profile={'game_data_rva':0x1000,'player_game_data_offset':16,'souls_offset':116}
        adapter.base=0x140000000;adapter.handle=123;adapter.k=Mock()
        adapter.alive=Mock(return_value=True);adapter.playable=Mock(return_value=True)
        adapter.context=Mock(return_value=(0x100000,0x110000,'m40_00_00_00'))
        pointers={adapter.base+0x1000:0x400000,0x400010:0x410000}
        adapter.ptr=Mock(side_effect=lambda address:pointers[address])
        values={0x410074:12345,0x410078:54321}
        adapter.integer=Mock(side_effect=lambda address:values[address])
        adapter.writable=Mock()
        writes=[]
        def write(handle,address,buffer,size,count):
            writes.append((address,size))
            values[address]=struct.unpack('<i',ctypes.string_at(buffer,size))[0]
            count._obj.value=size
            return True
        adapter.k.WriteProcessMemory.side_effect=write
        self.assertEqual(adapter.set_souls(1000000),1000000)
        self.assertEqual(writes,[(0x410074,4)])
        self.assertEqual(values[0x410078],54321)
        # A new character/data block after acquiring the write handle is refused.
        adapter.writable.side_effect=lambda:pointers.update({0x400010:0x510000})
        values[0x510074]=222
        with self.assertRaises(NotReady):adapter.set_souls(50000)
        self.assertEqual(len(writes),1)
        self.assertEqual(values[0x510074],222)

    def test_late_steam_mod_loader_refreshes_startup_detection(self):
        game=Path(self.temp.name)
        (game/'modengine.ini').write_text('[files]\nuseModOverrideDirectory=1\nmodOverrideDirectory="\\The Convergence"\n',encoding='utf-8')
        adapter=GameMemory.__new__(GameMemory)
        adapter.path=game/'DarkSoulsIII.exe'
        adapter.k=Mock();adapter.pid=123;adapter.variant_checked_at=10.0
        adapter.game_variant='vanilla';adapter.modded=False
        modules=[SimpleNamespace(name='DINPUT8.dll',path=str(game/'DINPUT8.dll'))]
        with patch('memory.entries',return_value=modules) as enumerate_modules, patch('memory.time.monotonic',return_value=11.0):
            adapter.refresh_variant()
            enumerate_modules.assert_not_called()
            self.assertEqual(adapter.game_variant,'vanilla')
        with patch('memory.entries',return_value=modules),patch('memory.time.monotonic',return_value=12.0):
            adapter.refresh_variant()
        self.assertEqual(adapter.game_variant,'convergence')
        self.assertTrue(adapter.modded)
        with patch('memory.entries',side_effect=OSError('transition')),patch('memory.time.monotonic',return_value=14.0):
            adapter.refresh_variant()
        self.assertEqual(adapter.game_variant,'convergence')

    def test_controller_refreshes_detection_before_mismatch_guard(self):
        self.c.set_variant('convergence')
        self.m.game_variant='vanilla'
        def refresh(force=False): self.m.game_variant='convergence'
        self.m.refresh_variant=Mock(side_effect=refresh)
        self.c.tick()
        self.assertTrue(self.c.variant_matches())
        self.assertFalse(self.c.active)
        self.assertEqual(self.m.writes,[])
        self.c.start(True,True)
        self.m.refresh_variant.assert_called_with(force=True)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT,prefix='test-')
        self.c=Controller(self.temp.name,ROOT,FakeMemory)
        self.now=100.0
        self.c.clock=lambda:self.now
        self.c.set_mode('placements')
        self.c.policy={'m33_00_00_00':{('c2140',3300210):True,('c2140',3300211):False}}
        self.c.tick()
        self.m=self.c.memory
        self.c.select(['c2140'])
    def tearDown(self): self.temp.cleanup()
    def start(self):
        self.c.start(True,True)
        self.c.tick()
        self.now+=2.0
    def test_loading_restores_and_never_applies(self):
        self.start();self.c.tick()
        self.m.loading=True;self.c.tick()
        self.assertEqual(self.m.flags[0x200000],bytearray([0x01,0x02]))
        writes=len(self.m.writes)
        self.c.tick()
        self.assertEqual(len(self.m.writes),writes)
        self.assertTrue(self.c.active)
        self.m.loading=False;self.c.tick()
        self.assertEqual(len(self.m.writes),writes)
        self.now+=0.9;self.c.tick()
        self.assertEqual(len(self.m.writes),writes)
        self.now+=0.2;self.c.tick()
        self.assertEqual(self.m.flags[0x200000],bytearray([0xE1,0x8A]))
    def test_completion_requires_all_loaded_targets_verified(self):
        self.start();self.c.tick()
        self.assertTrue(self.c.removal_complete)
        self.assertEqual((self.c.target_count,self.c.applied_count),(1,1))
        self.assertEqual(self.c.status,'제거 완료')
        writes=len(self.m.writes);self.c.tick()
        self.assertEqual(len(self.m.writes),writes)
        self.assertTrue(self.c.removal_complete)
        self.c.select(['c2140'])
        self.assertFalse(self.c.removal_complete)
        self.m.flags[0x200000]=bytearray([0,0])
        self.m.write_byte=lambda address,value:None
        self.c.tick()
        self.assertFalse(self.c.removal_complete)
        self.assertEqual(self.c.status,'몹 제거 중')
    def test_no_targets_and_paused_are_not_completed(self):
        self.start();self.c.tick();self.c.pause()
        self.assertFalse(self.c.removal_complete)
        self.start();self.m.ids=[];self.c.tick()
        self.assertEqual(self.c.status,'현재 불러온 제거 대상 없음')
        self.assertFalse(self.c.removal_complete)
        self.c.select([]);self.c.tick()
        self.assertEqual(self.c.status,'제거할 몬스터를 선택하세요.')
    def test_real_adapter_loading_and_fade_gate(self):
        adapter=GameMemory.__new__(GameMemory)
        adapter.base=0x100000
        adapter.profile={'loading_rva':100,'fade_rva':200}
        values={adapter.base+100:1,0x200000+0x2ec:0}
        adapter.integer=lambda address:values[address]
        adapter.ptr=lambda address:{adapter.base+200:0x150000,0x150008:0x200000}[address]
        self.assertFalse(adapter.playable())
        values[adapter.base+100]=0
        self.assertTrue(adapter.playable())
        values[0x200000+0x2ec]=1
        self.assertFalse(adapter.playable())
    def test_transition_between_byte_writes_restores(self):
        self.start()
        calls=[0]
        def playable():
            calls[0]+=1
            return calls[0]<3
        self.m.playable=playable
        self.c.tick()
        self.assertEqual(self.m.flags[0x200000],bytearray([0x01,0x02]))
        self.assertEqual(self.c.saved,{})
    def test_saved_selection_survives_restart(self):
        second=Controller(self.temp.name,ROOT,FakeMemory)
        self.assertEqual(second.selection,{'c2140'})
        self.assertFalse(second.active)
    def test_language_persists_without_changing_selection(self):
        self.start()
        self.c.set_language('en')
        second=Controller(self.temp.name,ROOT,FakeMemory)
        self.assertEqual(second.language,'en')
        self.assertEqual(second.selection,{'c2140'})
        self.assertTrue(self.c.active)
        self.c.set_language('ko')
        self.assertEqual(Controller(self.temp.name,ROOT,FakeMemory).language,'ko')
    def test_invalid_language_does_not_change_preferences(self):
        for value in ('fr',None,[],{},123):
            with self.assertRaises(ValueError): self.c.set_language(value)
        self.assertEqual(self.c.language,'ko')
    def test_english_names_and_policy_identical(self):
        original=self.c.state()
        self.assertEqual(set(EN_NAMES),set(self.c.manifest['catalog']))
        self.c.set_language('en');english=self.c.state()
        rows={r['id']:r for r in english['rows']}
        self.assertEqual(rows['c1190']['name'],'Cathedral Knight')
        self.assertEqual(rows['c2100']['name'],'Sewer Centipede')
        self.assertEqual(rows['c2140']['name'],'Basilisk')
        self.assertEqual(rows['c2120']['name'],'Mimic')
        self.assertEqual(next(m['name'] for m in english['maps'] if m['id']=='m35_00_00_00'),'Cathedral of the Deep')
        self.assertEqual(original['selection'],english['selection'])
        for r in original['rows']:
            self.assertEqual(r['category'],rows[r['id']]['category'])
            self.assertEqual(r['icon'],rows[r['id']]['icon'])
        for r in english['rows']:
            self.assertFalse(any('\uac00'<=c<='\ud7a3' for c in r['name']))
        for m in english['maps']:
            self.assertFalse(any('\uac00'<=c<='\ud7a3' for c in m['name']))
    def test_runtime_messages_in_english(self):
        self.assertEqual(translate('몹 제거 중','en'),'Removing enemies')
        self.assertEqual(translate('게임 실행을 기다리고 있습니다.','en'),'Waiting for DARK SOULS III.')
        self.assertEqual(translate('몹 제거 중','ko'),'몹 제거 중')
    def test_loader_presence_does_not_block_write_handle(self):
        adapter=GameMemory.__new__(GameMemory)
        adapter.modded=True
        adapter.pid=123
        adapter.handle=10
        adapter.k=SimpleNamespace(OpenProcess=Mock(return_value=20),CloseHandle=Mock())
        adapter.writable()
        self.assertEqual(adapter.handle,20)
        adapter.k.OpenProcess.assert_called_once_with(0x1038,False,123)
        adapter.k.CloseHandle.assert_called_once_with(10)
    def test_add_selection_while_monitoring(self):
        self.m.modded=True
        self.m.ids.append((0x400000,'c1190',3300300,0x500000))
        self.m.flags[0x400000]=bytearray([0,0])
        self.c.policy[self.m.ctx[2]][('c1190',3300300)]=True
        self.start();self.c.tick()
        self.assertEqual(self.m.flags[0x400000],bytearray([0,0]))
        self.c.select(['c2140','c1190']);self.c.tick()
        self.assertTrue(self.c.active)
        self.assertEqual(self.m.flags[0x400000],bytearray([0xE0,0x88]))
        self.assertEqual(self.m.flags[0x200000],bytearray([0xE1,0x8A]))
    def test_new_and_moved_placements_in_all_mode(self):
        self.c.set_mode('all')
        self.m.ids=[(0x200000,'c2140',999999,0x300000)]
        self.m.ctx=(0x100000,0x110000,'m99_99_99_99')
        self.start();self.c.tick()
        self.assertEqual(self.m.flags[0x200000],bytearray([0xE1,0x8A]))
    def test_known_protected_placement_still_excluded_in_all_mode(self):
        self.c.set_mode('all')
        self.m.ids=[(0x200000,'c2140',3300211,0x300000)]
        self.start();self.c.tick()
        self.assertEqual(self.m.writes,[])
    def test_boss_npc_unknown_player_excluded_in_all_mode(self):
        self.c.set_mode('all')
        for model,address in [('c5110',0x200000),('c1400',0x200000),('c9999',0x200000),('c2140',self.m.ctx[1])]:
            self.assertFalse(self.c.allowed((address,model,999999,0x300000),self.m.ctx))
    def test_mode_change_pauses_and_restores(self):
        self.c.set_mode('all');self.start();self.c.tick()
        self.c.set_mode('placements')
        self.assertFalse(self.c.active)
        self.assertEqual(self.m.flags[0x200000],bytearray([0x01,0x02]))
        self.assertEqual(self.c.selection,{'c2140'})
    def test_mode_persistence_and_old_preferences_migration(self):
        self.c.set_mode('all');self.c.set_language('en')
        second=Controller(self.temp.name,ROOT,FakeMemory)
        self.assertEqual((second.removal_mode,second.language),('all','en'))
        second.set_mode('placements');second.set_language('ko')
        third=Controller(self.temp.name,ROOT,FakeMemory)
        self.assertEqual((third.removal_mode,third.language),('placements','ko'))
        (Path(self.temp.name)/'settings.json').write_text('{"language":"en"}',encoding='utf-8')
        fourth=Controller(self.temp.name,ROOT,FakeMemory)
        self.assertEqual((fourth.removal_mode,fourth.language),('all','en'))
    def test_mod_warning_once_per_session_and_late_detection(self):
        self.c.set_mode('all');self.m.modded=True
        with self.assertRaises(ValueError):self.start()
        self.assertEqual(self.m.writes,[])
        self.c.start(True,True,True);self.c.tick();self.now+=2;self.c.tick()
        self.assertFalse(self.c.warning_required())
        self.c.pause();self.start();self.c.tick()
        self.c.mod_warning_ack=False;self.m.modded=False
        self.start();self.m.modded=True;self.c.tick()
        self.assertFalse(self.c.active)
        self.assertTrue(self.c.warning_required())
        self.assertEqual(self.m.flags[0x200000],bytearray([0x01,0x02]))
    def test_invalid_mode_rejected(self):
        for mode in ('unknown',None,[],{}):
            with self.assertRaises(ValueError):self.c.set_mode(mode)
    def test_boss_npc_unknown_selection_rejected(self):
        for values in (['c5110'],['c1400'],['c9999'],None,[1]):
            with self.assertRaises(ValueError): self.c.select(values)
    def test_default_diagnostic_never_writes(self):
        self.c.start(True,False);self.c.tick()
        self.assertEqual(self.m.writes,[])
    def test_offline_required(self):
        with self.assertRaises(ValueError): self.c.start(False,True)
    def test_candidate_flags_only_no_hp_writes(self):
        self.start();self.c.tick()
        self.assertEqual(self.m.flags[0x200000],bytearray([0xE1,0x8A]))
        self.assertEqual({a for a,v in self.m.writes},{0x201EE8,0x201EE9})
    def test_reloaded_entity_is_processed(self):
        self.start();self.c.tick()
        self.m.ids=[(0x400000,'c2140',3300210,0x500000)]
        self.m.flags[0x400000]=bytearray([0,0])
        self.c.tick()
        self.assertEqual(self.m.flags[0x400000],bytearray([0xE0,0x88]))
    def test_shared_model_protected_instance_untouched(self):
        self.m.ids.append((0x400000,'c2140',3300211,0x500000))
        self.m.flags[0x400000]=bytearray([0,0])
        self.start();self.c.tick()
        self.assertEqual(self.m.flags[0x400000],bytearray([0,0]))
    def test_unknown_placement_untouched(self):
        self.m.ids=[(0x200000,'c2140',12345,0x300000)]
        self.start();self.c.tick()
        self.assertEqual(self.m.writes,[])
    def test_player_untouched(self):
        self.m.ctx=(0x100000,0x200000,'m33_00_00_00')
        self.start();self.c.tick()
        self.assertEqual(self.m.writes,[])
    def test_stale_pointer_never_written(self):
        self.m.stale=True
        self.start();self.c.tick()
        self.assertEqual(self.m.writes,[])
    def test_unselect_restores_owned_bits_only(self):
        self.start();self.c.tick()
        self.m.flags[0x200000][1]|=0x20 # unrelated game flag changes while running
        self.c.select([]);self.c.tick()
        self.assertEqual(self.m.flags[0x200000],bytearray([0x01,0x22]))
    def test_pause_restores_valid_objects(self):
        self.start();self.c.tick();self.c.pause()
        self.assertFalse(self.c.active)
        self.assertEqual(self.m.flags[0x200000],bytearray([0x01,0x02]))
    def test_map_change_does_not_restore_old_pointers(self):
        self.start();self.c.tick();previous=len(self.m.writes)
        self.m.ctx=(0x100000,0x110000,'m39_00_00_00')
        self.c.tick();self.c.pause()
        self.assertEqual(len(self.m.writes),previous)
    def test_real_manifest_never_allows_boss_or_talking_placement(self):
        c=Controller(self.temp.name,ROOT,FakeMemory)
        for map_id,m in c.manifest['maps'].items():
            for p in m['placements']:
                if p['protected']:
                    self.assertFalse(c.policy[map_id].get((p['model'],p['entity']),False))

    def test_tabs_keep_independent_choices_and_restore_before_switch(self):
        self.start();self.c.tick()
        self.c.set_variant('convergence')
        self.assertFalse(self.c.active)
        self.assertEqual(self.m.flags[0x200000],bytearray([0x01,0x02]))
        self.assertEqual(self.c.selection,set())
        self.c.select(['c1103'])
        self.c.set_variant('cinders');self.c.select(['c7610'])
        self.c.set_variant('vanilla')
        self.assertEqual(self.c.selection,{'c2140'})
        self.c.set_variant('convergence')
        self.assertEqual(self.c.selection,{'c1103'})
        restarted=Controller(self.temp.name,ROOT,FakeMemory)
        self.assertEqual(restarted.game_variant,'convergence')
        self.assertEqual(restarted.selection,{'c1103'})
        restarted.set_variant('cinders')
        self.assertEqual(restarted.selection,{'c7610'})

    def test_old_selection_migrates_only_to_vanilla(self):
        self.c.select(['c2140'])
        (Path(self.temp.name)/'selection.json').write_text(json.dumps({'selection':['c2140']}))
        c=Controller(self.temp.name,ROOT,FakeMemory)
        c.set_variant('convergence');self.assertEqual(c.selection,set())
        c.set_variant('vanilla');self.assertEqual(c.selection,{'c2140'})

    def test_late_selection_request_cannot_cross_tabs(self):
        self.c.set_variant('convergence')
        with self.assertRaises(ValueError): self.c.select(['c2140'],'vanilla')
        self.assertEqual(self.c.selection,set())

    def test_profile_mismatch_blocks_start_and_pauses_existing_removal(self):
        self.start();self.c.tick()
        self.m.game_variant='convergence'
        self.c.tick()
        self.assertFalse(self.c.active)
        self.assertEqual(self.m.flags[0x200000],bytearray([0x01,0x02]))
        with self.assertRaises(ValueError): self.c.start(True,True)
        self.c.set_variant('convergence')
        self.assertTrue(self.c.variant_matches())

    def test_convergence_added_cemetery_models_and_new_bosses(self):
        self.c.set_variant('convergence');self.c.set_mode('all')
        ctx=(1,2,'m40_00_00_00')
        for model,entity in [('c1103',69006),('c1108',-1),('c1301',4000040),('c6262',-1),('c3101',4000035)]:
            self.c.select([model]);self.assertTrue(self.c.allowed((3,model,entity,4),ctx))
        for model,entity in [('c2255',4000800),('c3060',4000831),('c6021',4000830)]:
            self.assertFalse(self.c.allowed((3,model,entity,4),ctx))

    def test_mod_policies_exclude_every_registered_protected_placement(self):
        for variant in ('convergence','cinders'):
            self.c.set_variant(variant)
            self.c.set_mode('all')
            for map_id,m in self.c.manifest['maps'].items():
                for p in m['placements']:
                    if p['protected']:
                        self.assertFalse(self.c.allowed((3,p['model'],p['entity'],4),(1,2,map_id)),(variant,map_id,p))

    def test_unknown_profile_rejected_without_changing_running_state(self):
        self.start()
        with self.assertRaises(ValueError): self.c.set_variant('invalid')
        self.assertTrue(self.c.active)
        self.assertEqual(self.c.game_variant,'vanilla')

    def test_mod_english_state_includes_new_ids_and_original_labels(self):
        self.c.set_variant('cinders');self.c.set_language('en')
        rows={r['id']:r for r in self.c.state()['rows']}
        self.assertEqual(rows['c7610']['name'],'Red Crystal Lizard')
        self.assertEqual(rows['c7550']['category'],'보호 대상')
        self.c.set_variant('convergence')
        self.assertIn('c1103',{r['id'] for r in self.c.state()['rows']})

    def test_parameterized_mod_boss_calls_resolve_entity_ids(self):
        import struct
        from event_policy import boss_references
        health=struct.pack('<b3xi h2xi',1,0,0,900001)
        common={123: ([(2003,11,health)],[(0,4,0,4,0)])}
        events={0: ([(2000,6,struct.pack('<II',123,4000830)),
                    (2000,0,struct.pack('<III',0,456,4000831))],[]),
                456: ([(2003,12,bytes(4))],[(0,0,0,4,0)])}
        self.assertEqual(set(boss_references(events,common)),{4000830,4000831})

    def test_missing_event_arguments_are_not_guessed(self):
        from event_policy import boss_references
        events={0: ([(2003,12,bytes(4))],[(0,0,0,4,0)])}
        self.assertEqual(boss_references(events),{})


if __name__=='__main__': unittest.main(verbosity=2)
