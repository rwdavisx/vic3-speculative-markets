# Vanilla hooks for Speculative Markets: what script can read and write

Game found: **Victoria 3 1.15.0** (`caligula_branch.txt` = `release/1.15.0`; `built_against.txt` agrees).
Read-only research, 2026-11-11. Nothing was run in game.

Paths used below:
- `V` = `G:\SteamLibrary\steamapps\common\Victoria 3\game`
- `DOCS` = `C:\Users\rwdav\OneDrive\Documents\Paradox Interactive\Victoria 3\docs` (`triggers.log`, `effects.log`,
  `event_targets.log`, `modifiers.log`). **These logs are dated 2025-10-14, older than 1.15.** Anything 1.15 added
  (amendments, authority/legitimacy, interest tiers) is missing from them. Modifier names below were checked against
  1.15's own `V\common\modifier_type_definitions\*.txt` instead.
- "Mod uses" = the pattern already appears in `tools/*.py` and has run in the 1.15 observer runs (`data/obs_*v115*`).

Write levers are ranked by how they are applied: **static modifier** (on a law, tech, building or principle, always on),
**timed or permanent modifier** (`add_modifier`; supported on country, state, building, interest_group, institution,
power_bloc, character, journal_entry, political_movement; see `DOCS\effects.log` add_modifier), and **effect** (one shot).

---

## 1. Laws (economic system, trade policy, taxation, colonisation)

- **Read:** `has_law`, `has_law_or_variant` (mod uses), `is_enacting_law`, `enacting_any_law`, `law_approved_by`,
  `law_stance`, `enactment_chance_for_law`, `tax_level`, `has_consumption_tax`, `is_taxing_goods`
  (`DOCS\triggers.log`). Law keys in `V\common\laws\01_economic_system.txt` (traditionalism, interventionism, agrarianism,
  industry_banned, extraction_economy, laissez_faire, cooperative_ownership, command_economy), `01_trade_policy.txt`
  (mercantilism, protectionism, free_trade, isolationism, canton_system, sakoku), `01_taxation.txt`,
  `01_colonial_affairs.txt`.
- **Write:** `activate_law` (mod uses), `start_enactment`, `add_law_progress`, `add_enactment_modifier`,
  `add_enactment_setback`, `cancel_enactment`, `set_tax_level`, `add_taxed_goods`/`remove_taxed_goods`
  (`DOCS\effects.log`). Modifiers: `country_law_enactment_speed_mult`, `country_law_enactment_success_add`,
  `country_law_enactment_stall_mult`, `tax_*_add`, `country_tax_income_add` (mod uses), `state_tax_capacity_add/mult`.
  Laws themselves can carry any static modifier.
- **Slow lever:** strong. Enactment takes months (`lawgroup_economic_system` has `base_enactment_days = 150`,
  `V\common\law_groups\00_laws.txt`; up to 3 phases, `LAW_ENACTMENT_MAX_PHASES` in `V\common\defines\00_defines.txt`) and
  a failed attempt locks the law for 730 days (`LAW_ENACTMENT_COOLDOWN_DAYS`). The mod already reads economic system and
  trade policy as multipliers (`tools/vanilla_ties.py` `TRADE_TIE`; FINDINGS "Economic system law"). The mod can push back
  through `add_enactment_modifier` (a panic makes Laissez-faire harder to pass, a boom makes it easier).
  `on_law_enactment_started/pass/fail` and `on_law_activated` exist (`V\common\on_actions\00_code_on_actions.txt`).
- **Traps:** the mod shows its ties by overriding vanilla law definitions (`common/laws/zzz_spec_laws.txt`). That clashes
  with any other mod touching laws and must be regenerated each patch. AI law choice is hard to steer: per
  `V\common\laws\readme.md`, even `ai_enact_weight_modifier = 100000` may not pass a law.

## 2. Institutions

- **Read:** `has_institution`, `institution_investment_level`, `expanding_institution`, `shrinking_institution`.
- **Write:** `change_institution_investment_level`, `set_institution_investment_level`; `add_modifier` works on
  institution scope; `country_institution_<x>_max_investment_add` modifiers (one per vanilla institution, in
  `V\common\modifier_type_definitions`).
- **Slow lever:** good. Level moves about one step a year (`DAILY_INSTITUTION_SIZE_CHANGE = 0.0028`, levels 1 to 5)
  and costs bureaucracy every week. `on_investment_increased/decreased` fire on change.
- **Traps:** institutions only exist through a law (`institution = institution_x` on the law,
  e.g. `V\common\laws\00_internal_security.txt:36`), and the definition is just icon plus `modifier`
  (`V\common\institutions\institutions.md`). A mod institution (e.g. Banking Supervision) needs its own law **and** a
  matching `..._max_investment_add` modifier type; whether the engine wires a new institution's max level without code
  support is **unverified**.

## 3. Technologies

- **Read:** `has_technology_researched` (mod uses), `has_technology_progress`, `is_researching_technology`.
  Finance chain: `currency_standards, banking, stock_exchange, central_banking, joint_stock_companies, mutual_funds,
  investment_banks, international_exchange_standards, modern_financial_instruments, macroeconomics`
  (`V\common\technology\technologies\`).
- **Write:** `add_technology_progress`, `add_technology_researched`, `set_target_technology`; mod-added techs and
  tech modifiers (the mod already adds display modifiers per tech, `tools/tech_ties.py`). Modifiers for research speed exist.
- **Slow lever:** yes; research picks are a years-long player choice. `on_acquired_technology` fires per tech.
- **Traps:** few countries reach the late techs (FINDINGS: 11 of 520 reach Investment Banks by 1885), so gating
  Exchange steps on late techs leaves most of the world stuck.

## 4. Interest groups (Industrialists, Petite Bourgeoisie, Landowners)

- **Read:** `ig_approval`, `ig_clout`, `is_in_government` (mod uses), `has_ruling_interest_group`,
  `interest_group_population_percentage`, `is_interest_group_type`; `ig:ig_industrialists` etc. as scopes;
  `lobby_clout`.
- **Write:** modifiers `interest_group_ig_industrialists_approval_add` (mod uses),
  `interest_group_ig_petty_bourgeoisie_approval_add` (mod uses), `interest_group_ig_landowners_approval_add`,
  `interest_group_ig_<x>_pol_str_mult`, `interest_group_ig_<x>_pop_attraction_mult`; `add_modifier` on the IG itself;
  `set_ig_trait`, `add_ruling_interest_group`. Mod can add **political lobbies** (`V\common\political_lobbies\
  political_lobbies.md`: `can_create`, `join_weight`, appeasement factors), e.g. a foreign-creditor lobby.
- **Slow lever:** yes: who governs and IG clout shift over elections and years; a mod can let clout of
  Industrialists vs Landowners set bank appetite, and feed approval back.
- **Traps:** there is no `add_ig_approval` effect; approval only moves through modifiers. Approval swings make the
  government unstable, so keep them small (the mod's +/-2 is in line).

## 5. Companies

- **Read:** `any_company`/`every_company` (mod uses), `has_company`, `num_companies`, `max_num_companies`,
  `company_prosperity`, `company_is_prosperous`, `company_owned_levels`, `company_productivity`,
  `company_has_monopoly`, `is_company_type`, `can_establish_company` (mod uses); building `owning_company`.
- **Write:** `add_company`, `remove_company`, `add_company_monopoly`, `set_company_state_region`; country modifiers
  `country_company_throughput_bonus_add` (mod uses), `country_max_companies_add`, `country_free_charters_add`,
  `country_company_construction_efficiency_bonus_add`, `building_company_government_dividends_add`.
  Charter types are moddable data (`V\common\company_charter_types\company_charter_types.md`: type, cooldown, `possible`).
- **Slow lever:** moderate: which companies the player charters and builds up is a long choice; prosperity is a
  slow-moving read for "blue chips".
- **Traps:** `add_modifier` does **not** list company scope (`DOCS\effects.log`). Company bonuses come only from the
  static `prosperity_modifier` and executive modifiers in `company_types`. Executives are characters; no effect found to
  set them directly.

## 6. Power blocs

- **Read:** `is_in_power_bloc`, `is_power_bloc_leader`, `is_in_same_power_bloc`, `has_principle`,
  `has_principle_group`, `current_cohesion_percentage`, `leverage_advantage`, `power_bloc_rank`,
  `power_bloc_share_gdp`, `power_bloc_worst_economic_dependence`, `num_power_bloc_members`; `power_bloc` scope link.
- **Write:** `add_leverage`, `add_cohesion_number/percent`, `add_principle`/`remove_principle`, `join_power_bloc`,
  `add_modifier` on power_bloc. Modifiers: `power_bloc_leverage_generation_mult`, `power_bloc_cohesion_add/mult`,
  `country_leverage_generation_add/mult`, `power_bloc_allow_foreign_investment_lower_rank_bool`,
  `power_bloc_income_transfer_to_leader_factor`, `power_bloc_customs_union_bool`.
- **Mod principles:** principle groups and levels are data (`V\common\power_bloc_principle_groups\*.md`); principles
  carry only `member_modifier`, `leader_modifier`, `power_bloc_modifier`, `non_leader_modifier`, `institution_modifier`
  (`V\common\power_bloc_principles\00_power_bloc_principles.txt`). A "Financial Union" group is feasible.
- **Slow lever:** good for the World Centre tier: being leader of a bloc with `principle_group_foreign_investment`
  is a multi-year commitment.
- **Traps:** principles have no `on_activate` effects and need a bloc; most countries never join one.

## 7. Diplomacy (relations, pacts, treaties, investment rights, customs unions, subjects)

- **Read:** `relations:c:X` / `scope_relations`, `has_attitude`, `has_diplomatic_pact`, `num_diplomatic_pacts`,
  `any_scope_treaty`/`any_scope_article` (mod uses), `is_in_customs_union(_with)`, `is_subject_of`,
  `liberty_desire`, `income_transfer` (pact); country targets `mutual_trade_value_with_country`,
  `num_income_transfer_treaty_articles` (`DOCS\event_targets.log`).
- **Write:** `change_relations`, `add_change_relations_progress`, `create_diplomatic_pact`, `create_treaty`,
  `remove_diplomatic_pact`, `set_owes_obligation_to`; modifiers `country_improve_relations_speed_mult`,
  `country_treaty_leverage_generation_add`.
- **Mod treaty articles:** fully data-driven (`V\common\treaty_articles\treaty_articles.md`): `kind`, `cost`,
  `unlocked_by_technologies`, `quantity_min/max_value`, `source_/target_/mutual_modifier`, `requirement_to_maintain`,
  `on_entry_into_force`, `on_break`, AI weights. Vanilla `04_take_on_debt.txt` (needs Central Banking, calls
  `take_on_scaled_debt`) and `05_transfer_money.txt` are templates for a sovereign bond or bank-loan article.
  `07_foreign_investment_rights.txt` gates foreign building.
- **Slow lever:** strong. Treaties run years (`TREATIES_DEFAULT_LENGTH_YEARS = 5`, `V\common\defines\00_ai.txt`);
  relations drift. `on_treaty_entered_into_force`, `on_country_broke_treaty`, `on_treaty_dissolved` fire.
- **Traps:** 1.15 interest tiers gate who may sign foreign investment rights
  (`interest_tier_effect_can_sign_foreign_investment_rights` in `V\common\interest_tier_types\interest_tier_types.txt`), so an article may simply be
  unavailable. AI acceptance of a new article needs its `ai` block tuned; **untested**.

## 8. Trade (world market, trade centres, tariffs, treaty ports)

- **Read:** market triggers `market_goods_*` (mod uses `market_goods_sell_orders`, `market_goods_pricier`),
  `market_trade_reliance` (mod uses), `market_exports/imports`, `world_market_*`, `is_world_market_hub`,
  `state_trade`, `import_tariff_level`, `export_tariff_level`, `is_treaty_port`, `has_treaty_port_in_market`;
  targets `total_trade_value`, `num_world_market_hub_trade_center_levels`.
- **Write:** `set_import_tariff_level`, `set_export_tariff_level`, `add_exports/add_imports` (state_goods scope),
  `cede_treaty_port`; modifiers `state_trade_capacity_add/mult`, `building_trade_center_throughput_add`,
  `state_tariff_import_add/export_add`, `power_bloc_trade_advantage_add`, `state_trade_quantity_mult` (mod uses).
- **Slow lever:** yes. Trade Centres (`building_trade_center`, `V\common\buildings\11_private_infrastructure.txt`) are
  built over years and their levels in hub states are a natural "International Exchange" read.
- **Traps:** 1.15 has **no trade-route scope** (trade centres replaced routes; only `state_trade`, `market_trade`,
  `mutual_trade_value_with_country`). No effect sets a price.

## 9. Buildings and ownership

- **Read:** `has_building`, `b:X.level` (mod uses, `tools/vanilla_ties.py levels()`), `country_has_building_type_levels`,
  `country_has_building_group_levels`, `state_has_building_type_levels`, building `level`, `owning_company`,
  `country_ownership_fraction`, `private_ownership_fraction`, `self_ownership_fraction`, `cash_reserves_ratio`,
  `num_investments_of_type` (levels abroad), `gdp_ownership_ratio` / `gdp_owned_by` (mod uses).
  Keys: `building_financial_district` (bg_financial_districts), `building_manor_house`, `building_urban_center`,
  `building_trade_center`, `building_company_headquarter`.
- **Write:** `create_building`, `start_privately_funded_building_construction`, `remove_building`,
  `set_available_for_autonomous_investment`, `set_subsidized` (mod uses), `activate_production_method`; `add_modifier`
  on buildings; modifiers `building_throughput_add` (mod uses), `building_cash_reserves_mult`,
  `building_self_investment_chance_add`, `country_financial_districts_buy_farms_likelihood`.
- **Slow lever:** strongest read in the game: Financial District vs Manor House levels already set depth and steadiness
  (`tools/vanilla_ties.py`). `on_building_built`, `on_building_expanded` fire.
- **Traps:** summing levels needs `every_scope_state` loops; keep them monthly and cached (the mod does).

## 10. Investment pool and construction

- **Read:** `investment_pool` (mod uses), `investment_pool_gross_income` (mod uses), `investment_pool_net_income`,
  `construction_queue_num_queued_private_levels`, `construction_queue_private_duration`,
  `has_sufficient_construction_capacity_for_investment`, `has_wasted_construction`.
- **Write:** `add_investment_pool` (mod uses), `seize_investment_pool`; modifiers
  `state_<poptype>_investment_pool_contribution_add` and `_efficiency_mult` for capitalists, aristocrats, shopkeepers,
  clerks, etc. (mod uses three), `country_private_construction_allocation_mult` (mod uses), `state_construction_mult`
  (mod uses), `country_disable_investment_pool_bool`.
- **Slow lever:** yes, through law (Laissez-faire share), construction sector growth and pop mix.
- **Traps:** pool money that cannot be spent piles up; boosting contribution without construction capacity does little.

## 11. Treasury, debt, interest, credit

- **Read:** country targets `credit`, `principal`, `income`, `expenses`, `fixed_expenses`, `gdp`
  (`DOCS\event_targets.log`); triggers `scaled_debt` (mod uses), `in_default` (mod uses), `taking_loans` (mod uses),
  `can_take_on_scaled_debt`, `weekly_net_fixed_income`.
- **Write:** `add_treasury` (mod uses), `take_on_scaled_debt`, `clear_scaled_debt`, `clear_debt`; modifiers
  `country_loan_interest_rate_add/mult` (mod uses), `country_expenses_add` (mod uses), `building_cash_reserves_mult`.
- **Credit formula:** credit limit = total building cash reserves + `COUNTRY_MIN_CREDIT_BASE` (100000) +
  `COUNTRY_MIN_CREDIT_SCALED` (0.5) x GDP (`V\common\defines\00_defines.txt`). So `building_cash_reserves_mult` is the only
  modifier route to the vanilla credit ceiling found. `CREDIT_RATIO_HEALTH_THRESHOLD = 0.5`.
- **Slow lever:** debt builds over years; `on_country_default` / `on_country_no_longer_default` fire. War support already
  falls while borrowing (`WAR_SUPPORT_CHANGE_TAKING_LOANS_EFFECT = -0.5`).
- **Traps:** no "max credit" modifier type exists (searched all 2474 types for "credit"); cash-reserve boosts also
  change building behaviour, so test side effects. AI cuts wages and taxes on debt ratios (`00_ai.txt`), so the mod's
  interest changes move AI budgets.

## 12. Gold reserves and currency

- **Read:** `gold_reserves` (mod uses), `gold_reserves_limit`, `scaled_gold_reserves`.
- **Write:** only via `add_treasury`; modifiers `country_gold_reserve_limit_mult`, `country_minting_add/mult`,
  `goods_output_gold_add`.
- **Slow lever:** weak; reserves track the budget.
- **Traps:** vanilla has **no currency or exchange-rate system**; a gold standard must be wholly the mod's own variable.
  No `add_gold_reserves` effect.

## 13. Wars and diplomatic plays

- **Read:** `is_at_war` (mod uses), `has_war_with` (mod uses), `any_scope_war`, `war_exhaustion`,
  `has_diplomatic_play`, `is_diplomatic_play_enemy_of` (mod uses), `blockade_level`, `devastation` (mod uses).
- **Write:** `add_war_exhaustion`, `add_war_war_support`, `add_diplomatic_play_war_support`, `create_diplomatic_play`;
  war goals `force_nationalization`, `foreign_investment_rights`, `open_market` exist (`V\common\war_goal_types`).
- **Slow lever:** no; wars are events. Good as shocks (`on_diplo_play_war_start`, `on_war_end`, `on_capitulation`).
- **Traps:** AI play confidence already reads bankruptcy and gold (`DIPLO_PLAY_CONFIDENCE_FROM_*`, `00_ai.txt`).

## 14. Prestige and rank

- **Read:** `prestige` (mod uses), `country_rank` (mod uses), `global_country_ranking`, `gdp_ranking`,
  `gdp_per_capita_ranking`, `is_losing_power_rank`. Ranks: great_power, major_power, minor_power, insignificant_power,
  unrecognized_* (`V\common\country_ranks\00_country_ranks.txt`).
- **Write:** `country_prestige_add/mult` (mod uses both). No effect sets rank.
- **Slow lever:** yes: an Exchange's Standing can pay prestige every month, which feeds rank. `on_rank_changed` fires.
- **Traps:** prestige is a small share of rank score; large prestige grants would distort Great Power order.

## 15. Population, migration, wealth

- **Read:** pop `wealth` (mod uses), `strata` (mod uses), `average_sol`, `sol_ranking`, `total_population` (mod uses),
  `migration_pull`, `is_mass_migration_target`.
- **Write:** `add_pop_wealth`, `set_pop_wealth` (per pop; costly), `add_radicals`/`add_loyalists` (mod uses);
  modifiers `state_standard_of_living_add`, `state_middle/upper_strata_standard_of_living_add`,
  `building_capitalists/shopkeepers_standard_of_living_add`, `state_migration_pull_add/mult`,
  `country_mass_migration_attraction_mult`, `state_political_strength_from_wealth_mult`.
- **Slow lever:** yes: capitalist and shopkeeper counts in a state are a fair Exchange-depth read.
- **Traps:** per-pop effects across all states each month are expensive; prefer state modifiers.

## 16. Journal entries, decisions, scripted buttons, decrees, amendments

- **Journal entries / buttons / progress bars:** mod uses them throughout (`add_journal_entry`, `set_bar_progress`,
  `scripted_buttons`). Buttons can carry `autocomplete`, `visible`, `possible`, `ai_chance`
  (`V\common\scripted_buttons\scripted_buttons.md`). `on_journal_entry_activated/concluded` fire.
- **Decisions:** one-shot with `possible`; repeatable only with mod-made cooldowns.
- **Decrees** (`V\common\decrees\00_decree.txt`): state-level standing modifier, costs Authority (scales with rank),
  gated by `unlocking_technologies`/`unlocking_laws`, revalidated weekly. A "Chartered Exchange" decree on the capital
  is a cheap standing choice with an upkeep cost, but no enactment time.
- **Amendments (new since the docs):** `V\common\amendments\amendments.md`: attach to listed `allowed_laws`, carry
  `modifier` and `sponsor_modifier`, IG `would_sponsor`, `can_repeal` (legitimacy), `on_activate/on_deactivate`;
  effects `add_amendment` (e.g. `V\common\decisions\japan_decisions.txt:137`), `remove_amendment`; trigger
  `has_amendment`; `on_amendment_repealed`, `on_amendment_timeout`.

## 17. Law-like policy vehicles a mod can add

| vehicle | enactment time | IG politics | UI risk | cost to build |
|---|---|---|---|---|
| Scripted button + variable + delay (current Credit Policy) | mod-made timer | mod-made approval modifiers | none | lowest |
| Decree (state) | none; Authority upkeep | none | none | low |
| Amendment on economic-system laws | rides the law's enactment | native sponsorship | low | low to medium |
| Own law group + laws | native (`base_enactment_days`) | native stances, movements | **unverified**: new group in law panel | high (IG stances, AI) |
| Own institution | about a year per level | none | **unverified** | high (needs own law) |
| Power-bloc principle group | none | none | low | medium; bloc members only |

Lightest real enactment time: keep the scripted-button policy and add a "pending" variable that switches after N
months, as the mod does now. Next step up: amendments to `law_laissez_faire`/`law_interventionism`; whether a player
can add an amendment to an already active law outside an enactment is **unverified**.

---

## The 12 most valuable hooks

1. **Financial District and Manor House levels** (`b:X.level`, `country_has_building_type_levels`): already the
   depth and steadiness reads; natural Exchange Standing input.
2. **`building_cash_reserves_mult`**: the only modifier path to the vanilla credit ceiling; Standing can raise credit.
3. **`country_loan_interest_rate_add/mult`**: the mod's cleanest push into state finance (in use).
4. **Country targets `credit`, `principal`, `scaled_debt`, `in_default`, `on_country_default`**: vanilla debt
   driving panics and confidence.
5. **Investment pool modifiers** (`state_capitalists/shopkeepers/aristocrats_investment_pool_*`,
   `country_private_construction_allocation_mult`, `add_investment_pool`): booms and busts reach real construction.
6. **Foreign ownership reads** (`gdp_owned_by`, `num_investments_of_type`, `country_ownership_fraction`): measure an
   Exchange's international reach and contagion.
7. **Mod treaty article** modelled on `take_on_debt` / `transfer_money`: a multi-year bond or credit line between
   countries, with modifiers and break penalties.
8. **Economic-system and trade-policy laws** plus `add_enactment_modifier`: two-way, slow, already half built.
9. **IG approval modifiers** for Industrialists, Petite Bourgeoisie, Landowners, with `ig_clout` as a read.
10. **Prestige from Standing** (`country_prestige_add`) and `country_rank` / `on_rank_changed` as inputs.
11. **Trade Centre levels and `is_world_market_hub`**: the vanilla marker of a World Centre city.
12. **Finance tech chain** (banking to modern_financial_instruments) gating Standing steps, with tech-tooltip ties.

## Five that look tempting but do not work

1. **Modifiers on a company** (`add_modifier` does not support company scope). Only static `prosperity_modifier` in
   `company_types`; use country-level company modifiers instead.
2. **A vanilla currency or gold standard.** None exists; no exchange rate, no `add_gold_reserves`.
3. **Setting goods prices or the world market directly.** No effect sets price; only `add_exports/add_imports`,
   tariffs and taxed goods nudge it.
4. **Making a country a Great Power, or setting its rank.** No effect; only prestige and GDP move rank.
5. **Per-trade-route ties.** 1.15 has no trade-route scope; use `market_trade`, `state_trade`,
   `mutual_trade_value_with_country`. (Also known: map modes cannot be painted from script, FINDINGS line 776.)

## Unverified

- Docs logs predate 1.15; triggers and effects not used by the mod or seen in 1.15 script may have changed.
- A new law group or institution showing correctly in the 1.15 law and institution panels.
- AI acceptance of a mod treaty article; amendments on active laws outside an enactment.
- Exact side effects of `building_cash_reserves_mult` on building hiring and investment.
