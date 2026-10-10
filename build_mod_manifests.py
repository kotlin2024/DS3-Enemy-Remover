"""Generate compact identity metadata from locally installed mods (read-only).

Usage: python build_mod_manifests.py --convergence PATH --cinders PATH
No models, textures, maps, messages, parameters or scripts are redistributed.
"""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from catalog import CATALOG, MAP_NAMES, PHOBIA
from localization import EN_NAMES, EN_MAPS
from msb3 import enemies, unpack_dcx
from event_policy import read_events, boss_references

ROOT = Path(__file__).parent


def build(folder, variant, version):
    folder = Path(folder)
    common = read_events((folder/'event/common_func.emevd.dcx').read_bytes())
    maps, seen, labels, hashes = {}, defaultdict(list), defaultdict(Counter), {}
    for file in sorted((folder/'map/mapstudio').glob('*.msb.dcx')):
        blob = file.read_bytes()
        hashes['map/mapstudio/'+file.name] = hashlib.sha256(blob).hexdigest()
        map_id = file.name.removesuffix('.msb.dcx')
        event = folder/'event'/f'{map_id}.emevd.dcx'
        refs = {}
        if event.exists():
            event_blob = event.read_bytes()
            hashes['event/'+event.name] = hashlib.sha256(event_blob).hexdigest()
            refs = boss_references(read_events(event_blob), common)
        placements = []
        for enemy in enemies(unpack_dcx(blob)[0]):
            reason = None
            # Mod data, rather than vanilla boss coordinates, decides mod roles.
            if enemy.model == 'c0000' or enemy.talk > 0:
                reason = 'NPC'
            elif enemy.entity in refs or set(enemy.groups) & set(refs):
                reason = '보스 전투 개체'
            elif enemy.think <= 0:
                reason = 'NPC 또는 보조 개체'
            if re.match(r'(?i)^boss\s*:', enemy.name): reason = '보스 전투 개체'
            if re.match(r'(?i)^(?:npc|companion)\s*:', enemy.name): reason = 'NPC'
            placement = dict(model=enemy.model, entity=enemy.entity, protected=reason)
            placements.append(placement)
            seen[enemy.model].append(reason)
            if variant == 'cinders':
                match = re.match(r'(?i)^(?:enemy|boss|npc|companion)\s*:\s*(.+)', enemy.name)
                if match:
                    text = re.split(r'\s+-\s+|\s+\(', match[1])[0].strip()
                    if text and len(text) < 70: labels[enemy.model][text] += 1
        maps[map_id] = dict(name=MAP_NAMES.get(map_id, map_id), name_en=EN_MAPS.get(map_id, map_id),
                            placements=placements, protected_entities=sorted(refs))
    # Include known vanilla species too: mods may spawn these through scripts.
    catalog = deepcopy(CATALOG)
    for model, row in catalog.items():
        row['name_en'] = EN_NAMES[model]
        row['phobia'] = model in PHOBIA
    for model, reasons in seen.items():
        if model not in catalog:
            catalog[model] = dict(id=model, name=f'추가 몬스터 · {model}',
                                 name_en=f'Additional enemy · {model}', icon=None,
                                 category='괴물·동물', phobia=False)
        row = catalog[model]
        if all(reasons): row['category'] = '보호 대상'
        if labels[model]:
            names = [n for n, _ in labels[model].most_common(3)]
            # Preserve the names authored in the mod, without invented translations.
            row['name'] = row['name_en'] = ' / '.join(names)
            row['name_source'] = 'mod placement label'
    artwork = json.loads((ROOT/'assets/mod-art.json').read_text('utf-8')).get(variant, {})
    for model, art in artwork.items():
        if model in catalog:
            catalog[model].update(art)
    result = dict(maps=maps, catalog=catalog, version=version,
                  basis='local mod MSB identities and EMEVD boss references', hashes=hashes)
    (ROOT/f'placements_{variant}.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(variant, 'maps',len(maps),'placements',sum(len(m['placements']) for m in maps.values()),
          'models',len(catalog),'new models',len(set(seen)-set(CATALOG)),
          'boss references',sum(len(m['protected_entities']) for m in maps.values()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--convergence', required=True)
    parser.add_argument('--cinders', required=True)
    args = parser.parse_args()
    build(args.convergence, 'convergence', '2.2.1 local corpus')
    build(args.cinders, 'cinders', '2.15 local corpus')
