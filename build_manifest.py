"""Extract placement identities/policy; distribute no raw game maps."""
import hashlib
import json
import argparse
from pathlib import Path
from catalog import protection, CATALOG, MAP_NAMES
from msb3 import enemies, unpack_dcx

root = Path(__file__).parent
parser = argparse.ArgumentParser(description='Regenerate vanilla placement metadata from a local game installation.')
parser.add_argument('--game', type=Path, required=True, help='Dark Souls III Game directory')
source = parser.parse_args().game
policy = json.loads((root/'supported_maps.json').read_text('utf-8'))
maps = {}
for name, expected in policy['maps'].items():
    data = (source/'map'/'mapstudio'/name).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f'{name}: 원본 지문 불일치')
    raw, _ = unpack_dcx(data)
    map_id = name.removesuffix('.msb.dcx')
    rows = []
    for enemy in enemies(raw):
        rows.append(dict(model=enemy.model, entity=enemy.entity,
                         protected=protection(enemy,map_id)))
    maps[map_id] = dict(name=MAP_NAMES.get(map_id,map_id), placements=rows)
manifest = dict(maps=maps, catalog=CATALOG, basis='local supported map corpus, in-game verification pending')
(root/'placements.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
# Executable memory profiles are reviewed separately; metadata regeneration
# must not replace the validated profile or discard soul-control offsets.
print(len(maps),'maps;',sum(len(m['placements']) for m in maps.values()),'placement identities')
