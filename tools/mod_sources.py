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


# Tech & Res (Workshop 3472248460): building file stem -> {building: main good}; TR_UPGRADES: its other goods.
# It also defines Morgenroete's three goods and buildings itself (REPLACE_OR_CREATE), so they come from TR here.
TR = Path(os.environ['SPEC_TECHRES']).resolve() if os.environ.get('SPEC_TECHRES') else None
TR_SELLS = {
    'ztr_digital_buildings': {'office': 'business_data', 'software_industry': 'softwares',
                              'interactive_media_industry': 'interactive_entertainment',
                              'telecommunications_industry': 'telecommunications', 'datacenter_industry': 'organized_data',
                              'ecommerce_logistics': 'on_demand_goods'},
    'ztr_energy_buildings': {'hydroelectric_power_plant': 'global_electricity', 'renewable_energy_power_plant': 'global_electricity',
                             'geothermal_power_plant': 'global_electricity', 'fusion_power_plant': 'global_electricity'},
    'ztr_industrial_buildings': {'alloys_plant': 'alloys', 'electronics_industry': 'copperwires', 'battery_plant': 'batteries',
                                 'processors_foundry': 'processors', 'computer_assembly_plant': 'computer',
                                 'robotics_industry': 'robotics', 'aircraft_industry': 'civil_planes',
                                 'pharmaceuticals_industry': 'pharmaceuticals',
                                 'consumer_electronics_industry': 'homeappliances', 'space_assets_industry': 'space_assets'},
    'ztr_mr_buildings': {'uranium_mine': 'good_uranium'},
    'ztr_mr_modified_buildings': {'instrument_workshops': 'elgar_instruments', 'manzoni_publishing_industry': 'manzoni_prints',
                                  'mendelejew_hydrogenation_plants': 'light_fuel',
                                  'mendelejew_synthetic_rubber_factory': 'plastics'},
    'ztr_resources_buildings': {'water_plant': 'water', 'bauxite_mine': 'bauxite', 'commonores_mine': 'commonores',
                                'advancedores_mine': 'advancedores', 'natural_gas_rig': 'gas', 'rare_earths_mine': 'rare_earths'},
    # TR replaces these three vanilla buildings; the synthetics plant now makes cosmetics, not dye
    'ztr_vanilla_modified_buildings': {'automotive_industry': 'automobiles', 'synthetics_plant': 'cosmetics',
                                       'power_plant': 'electricity'},
}
# ponytail: secondary outputs counted from the start (tech None), as UPGRADES' None entries are
TR_UPGRADES = {'software_industry': [('interactive_entertainment', None)], 'datacenter_industry': [('ai_systems', None)],
               'alloys_plant': [('aluminium', None)], 'electronics_industry': [('electroniccomponents', None)],
               'aircraft_industry': [('aeroplanes', None)], 'consumer_electronics_industry': [('televisions', None)],
               'mendelejew_hydrogenation_plants': [('heavy_fuel', None), ('lubricant', None)],
               'mendelejew_synthetic_rubber_factory': [('rubber', None)], 'automotive_industry': [('tanks', None)],
               'power_plant': [('global_electricity', None)], 'telecommunications_industry': [('raw_data', None)]}
# no building makes these as a main or upgrade good: androids (no producer), elgar_music (a service, as in the Morgenroete patch)
TR_EXCLUDED = {'androids': 'No Tech & Res building produces it.',
               'elgar_music': 'Non-tradable service; outside the tradable-goods bridge scope, as in the Morgenroete patch.'}
TR_REPLACED = {'automotive_industry', 'synthetics_plant', 'power_plant'}  # removed from the vanilla stems under TR


def _goods_file(root, key):
    for path in sorted((root / 'common/goods').glob('*.txt')):
        if re.search(rf'^(?:\w+:)?{key}\s*=\s*\{{', path.read_text(encoding='utf-8-sig'), re.M):
            return path
    return None


def files(game, directory):
    """Effective files, respecting replacement by relative filename."""
    found = {p.name: p for p in (game / directory).glob('*.txt')}
    for mod in (MR, TR):
        if mod:
            found.update({p.name: p for p in (mod / directory).glob('*.txt')})
    return [found[name] for name in sorted(found)]


def source(game, relative, key=None):
    if TR and relative == 'common/goods/00_goods.txt' and key and (path := _goods_file(TR, key)):
        return path
    if TR and (TR / relative).is_file():
        return TR / relative
    if MR and relative == 'common/goods/00_goods.txt' and key in GOODS_FILES:
        return MR / 'common/goods' / (GOODS_FILES[key] + '.txt')
    if MR and (MR / relative).is_file():
        return MR / relative
    return game / relative


def validate_tr():
    """Fail loudly when Tech & Res changes the goods or buildings this registry names."""
    metadata = json.loads((TR / '.metadata/metadata.json').read_text(encoding='utf-8-sig'))
    if metadata.get('id') != 'tech.res':
        raise ValueError('SPEC_TECHRES must point to the installed Tech & Res mod')
    named = {g for m in TR_SELLS.values() for g in m.values()} | {g for u in TR_UPGRADES.values() for g, _ in u}
    for good in named - {'aeroplanes', 'tanks', 'rubber', 'electricity', 'automobiles'}:
        if not _goods_file(TR, good):
            raise ValueError(f'Tech & Res no longer defines {good}; review the registry')
    for stem, buildings in TR_SELLS.items():
        text = (TR / 'common/buildings' / (stem + '.txt')).read_text(encoding='utf-8-sig')
        for building in buildings:
            if not re.search(rf'^(?:\w+:)?building_{building}\s*=\s*\{{', text, re.M):
                raise ValueError(f'Tech & Res changed its building registry: {building}')


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
