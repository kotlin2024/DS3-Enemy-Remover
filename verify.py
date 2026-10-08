"""Lifecycle tests against an isolated fake process, never the real game."""
import json
from pathlib import Path
import tempfile
import unittest
from trainer import Controller, MASKS
from memory import GameMemory, NotReady
from types import SimpleNamespace
from unittest.mock import Mock
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


if __name__=='__main__': unittest.main(verbosity=2)
