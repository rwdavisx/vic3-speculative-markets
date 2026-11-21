"""Category confirmation for individual goods. Use the last completed pulse for every good in the next one."""

CHART_NAMED_SECTORS = 4
CATEGORY_WEIGHT = 0.5
CATEGORIES = ("staple", "industrial", "luxury", "military")


# One market sector per tracked good.
GROUPS = {
    "food": ("Food & Provisions", "grain fish meat fruit groceries sugar water"),
    "plantation": ("Plantation Trades", "tea coffee tobacco opium wine liquor"),
    "household": ("Textiles & Household Goods", "fabric silk dye clothes luxury_clothes furniture luxury_furniture porcelain fine_art cosmetics homeappliances elgar_instruments manzoni_prints on_demand_goods"),
    "materials": ("Timber, Metals & Materials", "wood hardwood iron copper lead steel glass paper advancedores alloys aluminium bauxite commonores rare_earths"),
    "energy": ("Fuel & Power", "coal oil electricity gas global_electricity good_uranium heavy_fuel light_fuel lubricant batteries"),
    "industry": ("Machinery & Chemicals", "tools engines rubber sulfur fertilizer explosives plastics pharmaceuticals robotics"),
    "transport": ("Transport & Shipping", "clippers steamers merchant_marine automobiles civil_planes space_assets"),
    "defence": ("Arms & Ordnance", "small_arms artillery ammunition tanks aeroplanes"),
    "communications": ("Electronics & Communications", "telephones radios ai_systems business_data computer copperwires electroniccomponents interactive_entertainment organized_data processors raw_data softwares telecommunications televisions"),
}
BY_GOOD = {g: key for key, (_, goods) in GROUPS.items() for g in goods.split()}
assert len(BY_GOOD) == sum(len(goods.split()) for _, goods in GROUPS.values())


def price_signal(good, category):
    raw = f"spec_price_spread_{good}"
    mean = f"spec_cat_trend_{category}"
    review = f"spec_review_{category}"
    return f"""{raw} = {{
    value = var:spec_fast_{good}
    subtract = var:spec_slow_{good}
}}
{sector_slice(good, category)}
{supported_value(f"spec_supported_spread_{good}", raw, mean)}
{supported_value(f"spec_review_spread_{good}", raw, review)}
spec_review_sector_{good} = {tuple(GROUPS).index(category)}
spec_review_has_{good} = {{ value = 0 if = {{ limit = {{ has_variable = {review} }} value = 1 }} }}
spec_review_mean_{good} = {{ value = 0 if = {{ limit = {{ has_variable = {review} }} value = var:{review} }} }}
spec_review_reduction_{good} = {{
    value = 0
    if = {{
        limit = {{ NOT = {{ {raw} = 0 }} }}
        value = 1
        subtract = {{ value = spec_review_spread_{good} divide = {raw} }}
        min = 0
        max = {CATEGORY_WEIGHT:g}
    }}
}}"""


def sector_slice(good, category):
    if good == "fish":  # The chart uses a separate goods scope for the combined remainder.
        category = "other"
    elif good != GROUPS[category][1].split()[0]:
        return ""
    return (f"spec_sector_slice_{good} = {{ value = 0 if = {{ limit = {{ has_variable = spec_sector_share_{category} }} "
            f"value = var:spec_sector_share_{category} }} }}")


def supported_value(name, raw, mean):
    return f"""{name} = {{
    value = {raw}
    if = {{
        limit = {{ has_variable = {mean} }}
        multiply = {1 - CATEGORY_WEIGHT:g}
        add = {{
            value = var:{mean}
            if = {{ limit = {{ {raw} >= 0 }} min = 0 max = {raw} }}
            else = {{ max = 0 min = {raw} }}
            multiply = {CATEGORY_WEIGHT:g}
        }}
    }}
}}"""


def start(categories, indent):
    return "".join(f"{indent}set_local_variable = {{ name = spec_cat_{field}_{cat} value = 0 }}\n"
                   for cat in categories for field in ("sum", "weight"))


def accumulate(good, category, indent):
    # Scale turnover before multiplying by the price spread. Market shares and spreads are bounded.
    return (f"{indent}set_local_variable = {{ name = spec_cat_weight value = {{ value = spec_mv_{good} divide = var:spec_mv_total }} }}\n"
            f"{indent}change_local_variable = {{ name = spec_cat_weight_{category} add = local_var:spec_cat_weight }}\n"
            f"{indent}change_local_variable = {{ name = spec_cat_sum_{category} add = {{ value = spec_price_spread_{good} multiply = local_var:spec_cat_weight }} }}\n")


def chart_order_value():
    lines = [f"if = {{ limit = {{ this = g:{members.split()[0]} }} value = scope:spec_sector_owner.var:spec_sector_share_{sector} }}"
             for sector, (_, members) in GROUPS.items()]
    return "spec_sector_order = {\nvalue = 0\n" + "\n".join(lines) + "\n}\n"


def rank_chart():
    # The candidate list is in sector order. Only positive shares are candidates.
    record = []
    for sector, (_, members) in GROUPS.items():
        record.append(f"if = {{ limit = {{ prev = {{ this = g:{members.split()[0]} }} }} "
                      f"set_variable = {{ name = spec_sector_rank_{sector} value = var:spec_sector_position }} "
                      f"change_variable = {{ name = spec_sector_share_other add = var:spec_sector_share_{sector} }} }}")
    reset = "\n".join(f"remove_variable = spec_sector_rank_{sector}" for sector in GROUPS)
    return f"""spec_refresh_sector_chart = {{
        save_temporary_scope_as = spec_sector_owner
        clear_variable_list = spec_sector_ranked
        set_variable = {{ name = spec_sector_position value = 0 }}
        set_variable = {{ name = spec_sector_share_other value = 0 }}
        {reset}
        ordered_in_list = {{
            variable = spec_sector_chart
            order_by = spec_sector_order
            scope:spec_sector_owner = {{
                change_variable = {{ name = spec_sector_position add = 1 }}
                if = {{ limit = {{ var:spec_sector_position <= {CHART_NAMED_SECTORS} }} add_to_variable_list = {{ name = spec_sector_ranked target = prev }} }}
                else = {{ {chr(10).join(record)} }}
            }}
        }}
        if = {{ limit = {{ var:spec_sector_share_other > 0 }} add_to_variable_list = {{ name = spec_sector_ranked target = g:fish }} }}
        remove_variable = spec_sector_position
    }}
"""


def finish(categories, indent):
    return (f"{indent}clear_variable_list = spec_sector_chart\n"
            + "".join(f"{indent}if = {{ limit = {{ OR = {{ is_player = yes market ?= {{ owner ?= root }} }} }}\n"
                   f"{indent}    set_variable = {{ name = spec_sector_share_{cat} value = local_var:spec_cat_weight_{cat} }}\n"
                   f"{indent}    if = {{ limit = {{ local_var:spec_cat_weight_{cat} > 0 }} add_to_variable_list = {{ name = spec_sector_chart target = g:{GROUPS[cat][1].split()[0]} }} }}\n"
                   f"{indent}    if = {{ limit = {{ has_variable = spec_cat_trend_{cat} }} set_variable = {{ name = spec_review_{cat} value = var:spec_cat_trend_{cat} }} }}\n"
                   f"{indent}    else = {{ remove_variable = spec_review_{cat} }}\n{indent}}}\n"
                   f"{indent}if = {{\n"
                   f"{indent}\tlimit = {{ local_var:spec_cat_weight_{cat} > 0 }}\n"
                   f"{indent}\tset_variable = {{ name = spec_cat_trend_{cat} value = {{ value = local_var:spec_cat_sum_{cat} divide = local_var:spec_cat_weight_{cat} }} }}\n"
                   f"{indent}}}\n{indent}else = {{ remove_variable = spec_cat_trend_{cat} }}\n" for cat in categories))
