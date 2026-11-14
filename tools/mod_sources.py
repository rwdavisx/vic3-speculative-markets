"""Build-time Morgenroete registry. No upstream files are copied into releases."""
import os
import re
import json
from pathlib import Path

MR = Path(os.environ['SPEC_MORGENROETE']).resolve() if os.environ.get('SPEC_MORGENROETE') else None
SELLS = {
    'mr_arts_elgar_buildings': {'instrument_workshops': 'elgar_instruments'},
    'mr_science_curie_buildings': {'uranium_mine': 'good_uranium'},
    'mr_arts_manzoni_buildings': {'manzoni_publishing_industry': 'manzoni_prints'},
}
GOODS_FILES = {'elgar_instruments': 'elgar_goods', 'good_uranium': 'curie_goods',
               'manzoni_prints': 'manzoni_goods'}


def files(game, directory):
    """Effective files, respecting replacement by relative filename."""
    found = {p.name: p for p in (game / directory).glob('*.txt')}
    if MR:
        found.update({p.name: p for p in (MR / directory).glob('*.txt')})
    return [found[name] for name in sorted(found)]


def source(game, relative, key=None):
    if MR and relative == 'common/goods/00_goods.txt' and key in GOODS_FILES:
        return MR / 'common/goods' / (GOODS_FILES[key] + '.txt')
    if MR and (MR / relative).is_file():
        return MR / relative
    return game / relative


def validate():
    if not MR:
        return
    if not (MR / '.metadata/metadata.json').is_file():
        raise ValueError('SPEC_MORGENROETE must point to the installed Morgenroete mod')
    metadata = json.loads((MR / '.metadata/metadata.json').read_text(encoding='utf-8-sig'))
    if metadata.get('id') != '2889925770':
        raise ValueError('Unexpected Morgenroete mod identity')
    goods = {key for path in (MR / 'common/goods').glob('*.txt')
             for key in re.findall(r'^(\w+)\s*=\s*\{', path.read_text(encoding='utf-8-sig'), re.M)}
    if goods != set(GOODS_FILES) | {'air_travel', 'elgar_music'}:
        raise ValueError(f'Morgenroete goods changed; review the registry: {sorted(goods)}')
    for stem, buildings in SELLS.items():
        text = (MR / 'common/buildings' / (stem + '.txt')).read_text(encoding='utf-8-sig')
        for building in buildings:
            if not re.search(rf'^building_{building}\s*=\s*\{{', text, re.M):
                raise ValueError(f'Morgenroete changed its building registry: {building}')
