from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools/tuner"))
import engine
import lab


class TunerParityTests(unittest.TestCase):
    def test_sentiment_staggered_starts_full_terms_and_fresh_evidence(self):
        e = self.economy("passive")
        e.law_mult[:] = 1
        e.share[:] = 0
        e.share[0, :3] = [0.001, 0.04, 0]
        e.sentiment_case[:] = e.sentiment_term[:] = 0
        prices = np.zeros_like(e.share)
        prices[0, :3] = [0.10, 0, 0.75]
        roll = np.array([[0.999, 0.999]])
        for month in range(1, 19):
            if month == 4:
                prices[0, 1] = -0.10
            if month == 7:
                prices[0, 0] = -0.30
            e.advance_sentiment(prices, roll)
            self.assertEqual(e.sentiment_term[0, 0], 18 - month if 6 <= month <= 17 else 0)
            self.assertEqual(e.sentiment_term[0, 1], month - 21 if month >= 9 else 0)
            self.assertEqual(e.sentiment_term[0, 2], 0)
        self.assertEqual(e.sentiment_case[0, 0], -1)

    def test_sentiment_quiet_roll_caps_and_law_exit(self):
        e = self.economy("passive")
        e.law_mult[:] = 1
        e.share[:] = 0.02
        prices = np.full_like(e.share, 0.20)
        prices[:, 4:] *= -1
        for _ in range(10):
            e.advance_sentiment(prices, np.zeros((1, 2)))
        self.assertFalse(e.sentiment_term.any())
        for _ in range(6):
            e.advance_sentiment(prices, np.full((1, 2), 0.999))
        self.assertEqual((e.sentiment_term > 0).sum(), 3)
        self.assertEqual((e.sentiment_term < 0).sum(), 2)
        e.law_mult[:] = 0
        e.advance_sentiment(prices, np.full((1, 2), 0.999))
        self.assertFalse(e.sentiment_term.any())
        self.assertFalse(e.sentiment_case.any())

    def test_established_goods_have_two_tickets_to_a_small_goods_one(self):
        e = self.economy("passive", n=7)
        e.law_mult[:] = 1
        e.share[:] = 0
        e.share[:, :2] = [0.001, 0.01]
        e.sentiment_case[:] = e.sentiment_term[:] = 0
        e.sentiment_case[:, :2] = 5
        rolls = np.zeros((7, 2))
        rolls[:, 0] = (np.arange(7) + 0.5) / 7
        e.advance_sentiment(np.full_like(e.share, 0.10), rolls)
        self.assertEqual((e.sentiment_term[:, 0] > 0).sum(), 1)
        self.assertEqual((e.sentiment_term[:, 1] > 0).sum(), 2)
        self.assertEqual((e.sentiment_term.sum(1) == 0).sum(), 4)

    def test_requested_credit_policy_waits_for_research_and_cooldown(self):
        e = self.economy("passive", configure=lambda cfg: cfg.update(player_credit="tight"))
        e.stance[:] = 0
        e.tech_at["central_banking"][:] = 1000
        e.decide()
        self.assertEqual(e.stance[0], 0)
        e.tech_at["central_banking"][:] = 0
        e.stance_cd[:] = 1
        e.decide()
        self.assertEqual(e.stance[0], 0)
        e.stance_cd[:] = 0
        e.decide()
        self.assertEqual(e.stance[0], -1)
        self.assertEqual(e.stance_cd[0], e.K["STANCE_COOLDOWN"])

    def test_charter_prerequisites_first_grant_lock_and_trust_cost(self):
        e = self.economy("passive")
        e.tech_at["banking"][:] = e.tech_at["stock_exchange"][:] = 1000
        self.assertFalse(e.grant_charter("money")[0])
        e.tech_at["banking"][:] = 0
        before = e.trust[0]
        self.assertTrue(e.grant_charter("money")[0])
        self.assertEqual(e.trust[0], before)
        self.assertFalse(e.grant_charter("commodity")[0])
        e.m += engine.centres.CHARTER_LOCK * 12
        self.assertFalse(e.grant_charter("share")[0])
        e.tech_at["stock_exchange"][:] = 0
        self.assertTrue(e.grant_charter("share")[0])
        self.assertEqual(e.trust[0], before * (1 - engine.centres.CHARTER_COST))

    def test_money_market_cushions_same_reckless_month(self):
        e = self.economy("passive")
        e.econ[:] = "interventionism"
        e.money_base[:] = "gold_standard"
        e.set_laws(range(e.n))
        e.tech_at["banking"][:] = 0
        e.grant_charter("money")
        e.lax[:], e.trust[:] = 0.95, 60
        e.step()
        self.assertAlmostEqual(e.trust[0], 60 - 0.8 * engine.centres.KNOWN_LOSS)

    def test_price_response_preserves_direction_and_confirmation(self):
        def rising(peer):
            e = self.economy("passive")
            e.boom_p[:] = 0
            e.ep_t[:] = -1
            e.ep_t[0, 0], e.ep_d[0, 0], e.ep_x[0, 0] = 2, 12, 1
            e.glut[:] = 0
            e.category_trend[:] = peer
            e.step()
            return e.h_raw[0, :2]
        neutral, isolated, broad = rising(np.nan), rising(-1), rising(1)
        self.assertAlmostEqual((isolated[0] - 1) * 2, broad[0] - 1)
        self.assertGreater(isolated[0], 1)
        self.assertAlmostEqual(broad[0], neutral[0])
        self.assertEqual(broad[1], 1)

    def test_identical_falling_price_input_responds_to_tight_credit(self):
        def close_episode(stance):
            e = self.economy("passive")
            e.boom_p[:] = 0
            e.ep_t[:] = -1
            e.ep_d[0, 0], e.ep_t[0, 0], e.ep_end[0, 0] = 12, 11, 0.35
            e.glut[:] = 0
            e.category_trend[:] = 0
            e.stance[:] = stance
            e.step()
            return e.h_raw[0, 0], e.category_trend.copy()
        normal, before = close_episode(0)
        tight, after = close_episode(-1)
        np.testing.assert_allclose(after, before, equal_nan=True)
        self.assertLess(normal, tight)
        self.assertLess(tight, 1)

    def test_result_flags_a_ceiling_that_clips_the_final_technology_tier(self):
        e = self.economy()
        for tech in engine.LADDER_TECHS:
            e.tech_at[tech][:] = 0
        top = engine.lv.LADDER[-1]
        for ceiling in (top - 2, top, top + 2):
            e.K["LEV_RUIN"] = ceiling
            self.assertEqual(e.credit_limit()[0], min(ceiling, top))
            self.assertEqual(bool(lab.credit_tier_note(e.K)), ceiling < top)

    def test_restrained_good_gets_half_the_normal_lending_pull(self):
        e = self.economy("passive")
        e.trace, e.hist = True, []
        e.boom_p[:] = 0
        e.ep_t[:] = -1
        e.ep_t[0, 0], e.ep_d[0, 0], e.ep_x[0, 0] = 4, 12, 6
        e.lever[0, 0], e.share[0, 0] = -1, 0.05
        e.lax[:] = 0.5
        e.step()
        heat = np.clip((e.h[0, 0] - 1) / 5, 0, 1)
        expected = 0.05 * heat * e.K["EXP_PULL"] * engine.exposure.RESTRAINED
        self.assertGreater(expected, 0)
        self.assertAlmostEqual(e.hist[-1]["boom_share"], expected, places=4)

    def test_reckless_month_under_gold_scales_trust_loss(self):
        e = self.economy("passive")
        e.econ[:] = "interventionism"
        e.money_base[:] = "gold_standard"
        e.set_laws(range(e.n))
        e.lax[:], e.trust[:] = 0.95, 60
        e.step()
        self.assertAlmostEqual(e.trust[0], 59.2)

    def economy(self, bot="ai", n=1, configure=None):
        cfg = engine.defaults()
        if configure:
            configure(cfg)
        e = engine.Economies(engine.current(), cfg, bot, n, 7)
        e.step()
        return e

    def test_research_requires_prerequisites(self):
        def scenario(cfg):
            cfg["inputs"]["observed_research"] = 0
            cfg["tech_years"].update(investment_banks=[1, 1], mutual_funds=[3, 3], central_banking=[9, 9])
        e = self.economy(configure=scenario)
        self.assertGreaterEqual(e.tech_at["investment_banks"][0], 9 * 12)
        self.assertGreaterEqual(e.tech_at["mutual_funds"][0], 9 * 12)

    def test_modeled_goods_cannot_exceed_entire_market(self):
        def scenario(cfg):
            cfg["inputs"].update(goods=[24, 24], good_share=[0.2, 0.2])
        e = self.economy(configure=scenario)
        self.assertLessEqual(e.share.sum(), 1 + 1e-12)

    def test_central_banking_and_six_month_lock(self):
        e = self.economy("reckless")
        e.tech_at["central_banking"][:] = 100
        for _ in range(2):
            e.step()
            self.assertEqual(e.stance[0], 0)
        e.tech_at["central_banking"][:] = 0
        e.step()
        self.assertEqual(e.stance[0], 1)
        # Force the bot to want Normal on every subsequent pulse.
        e.pol = dict(e.pol, unloose_conf=-1)
        for left in range(engine.g.STANCE_COOLDOWN - 1, 0, -1):
            e.step()
            self.assertEqual((e.stance[0], e.stance_cd[0]), (1, left))
        e.step()
        self.assertEqual((e.stance[0], e.stance_cd[0]), (0, engine.g.STANCE_COOLDOWN))

    def test_ai_tight_credit_waits_six_pulses_before_return_to_normal(self):
        e = self.economy(configure=lambda cfg: cfg["inputs"].update(fiscal_profiles=0))
        e.tech_at["central_banking"][:] = 99
        e.pol = dict(e.pol, tight_conf=-1, loose_conf=-1)
        e.step()
        self.assertEqual(e.stance[0], 0)
        e.tech_at["central_banking"][:] = 0
        e.step()
        self.assertEqual((e.stance[0], e.stance_cd[0]), (-1, 6))
        e.pol = dict(e.pol, tight_conf=101, tight_lev=100, untight_conf=101, untight_lev=100)
        for left in range(5, 0, -1):
            e.step()
            self.assertEqual((e.stance[0], e.stance_cd[0]), (-1, left))
        e.step()
        self.assertEqual((e.stance[0], e.stance_cd[0]), (0, 6))

    def test_ai_cannot_spend_same_gold_on_rescue_and_buyup(self):
        e = self.economy()
        e.tech_at["banking"][:] = 0
        e.in_panic[:] = True
        e.panic[:] = 4
        e.crunch[:] = 10
        e.sdebt[:] = 0
        e.reserves[:] = e.rescue_cost()
        e.ai_u[:] = 0
        e.decide()
        self.assertTrue(e.did_rescue[0])
        self.assertFalse(e.did_bailout[0])
        self.assertAlmostEqual(e.reserves[0], 0)

    def test_buyup_cannot_be_used_in_default_by_player(self):
        e = self.economy("reckless")
        e.in_default = np.ones(e.n, bool)
        e.tech_at["banking"][:] = 0
        e.crunch[:] = 10
        e.decide()
        self.assertFalse(e.did_bailout[0])

    def test_ai_cannot_rescue_when_nearly_bankrupt(self):
        e = self.economy()
        e.nearly_broke = np.ones(e.n, bool)
        e.tech_at["banking"][:] = 0
        e.in_panic[:] = True
        e.panic[:] = 4
        e.reserves[:] = 1
        e.sdebt[:] = 0
        e.ai_u[:] = 0
        e.decide()
        self.assertFalse(e.did_rescue[0])

    def test_long_depression_requires_a_new_eligible_origin(self):
        e = self.economy()
        w = e.worlds
        w.opens[:] = 10
        w.can_repeat[:] = True
        panic = np.zeros((1, w.powers), bool)
        panic[0, 0] = True
        self.assertFalse(w.advance(9, panic)[1].any())
        self.assertFalse(w.advance(10, np.zeros_like(panic))[1].any())
        self.assertTrue(w.advance(11, panic)[1][0])
        reopen = int(w.opens[0])
        panic[0, 1] = True
        self.assertFalse(w.advance(reopen - 1, panic)[1][0])
        panic[0, 1] = False
        self.assertFalse(w.advance(reopen, panic)[1][0])
        panic[0, 1] = True
        self.assertTrue(w.advance(reopen + 1, panic)[1][0])
        self.assertFalse(w.advance(int(w.opens[0]), np.ones_like(panic))[1][0])

    def test_ai_selects_affordable_good_and_requires_surplus(self):
        e = self.economy()
        e.auth[:] = 100
        e.lever[:] = 0
        e.lever_cost[:] = 40
        e.lever_cost[0, 0] = 60
        e.risk[:] = 0
        e.risk[0, :2] = [20, 10]
        e.conf[:] = 100
        e.ai_levers(np.zeros(e.n))
        self.assertEqual(e.lever[0, :2].tolist(), [0, -1])
        e.lever[:] = 0
        e.conf[:] = 0
        e.word[:] = engine.levers.CALM_WORD
        e.subsidy[:] = 0.001
        e.net_income[:] = 0.001 * engine.levers.AI_FUNDS
        e.ai_levers(np.zeros(e.n))
        self.assertFalse((e.lever > 0).any())
        e.net_income[:] += 0.0001
        e.ai_levers(np.zeros(e.n))
        self.assertEqual((e.lever > 0).sum(), 1)
        e.net_income[:] = -0.001
        e.ai_levers(np.zeros(e.n))
        self.assertFalse((e.lever > 0).any())

    def test_act_suspension_shortens_panic_at_full_strength(self):
        e = self.economy()
        e.enacted["currency"][:] = True
        e.in_panic[:] = True
        e.panic[:] = 5
        e.reserves[:] = 0
        e.ai_journal(np.ones((e.n, 3)))
        self.assertTrue(e.rescued[0])
        self.assertEqual(e.panic[0], engine.journal.SUSPEND_MONTHS)
        e.feedback()
        self.assertEqual(e.panic_tp[0], e.K["PANIC_THROUGHPUT"])

    def test_equal_calm_goods_follow_generated_good_order(self):
        e = self.economy()
        e.auth[:] = 1000
        e.lever[:] = 0
        e.conf[:] = 0
        e.net_income[:] = 0.1
        e.word[:] = 0
        e.word[0, :2] = engine.levers.CALM_WORD
        e.goods_ids[0, :2] = [15, 5]
        e.h[0, :2] = 1
        e.ai_levers(np.zeros(e.n))
        self.assertEqual(e.lever[0, :2].tolist(), [0, 1])

    def test_custom_fiscal_ranges_and_minimum_treasury_cost(self):
        def scenario(cfg):
            cfg["inputs"].update(fiscal_profiles=0, reserves=[0.02, 0.02], weekly_balance=[0, 0])
        e = self.economy(configure=scenario)
        self.assertAlmostEqual(e.reserves[0], 0.02)
        e.gdp[:] = 100000
        self.assertAlmostEqual(e.treasury_price(np.array([0.0001]))[0], 0.01)

    def test_peers_only_draw_great_power_finances_in_each_era(self):
        e = self.economy(n=9)
        _, p = engine.fiscal.profiles()
        self.assertEqual(e.worlds.peers.fiscal_ranks.shape[0], len(p["gp"]))
        peers = e.worlds.peers
        for era, ranks in enumerate(peers.fiscal_ranks):
            selected = ranks[:e.worlds.powers][peers.fiscal_gp[era, :e.worlds.powers]]
            self.assertTrue(p["gp"][era, selected].all())
            self.assertEqual(len(np.unique(selected)), int(p["gp"][era].sum()))

    def test_observed_country_research_dates_bound_unlocks(self):
        e = self.economy(n=16)
        _, p = engine.fiscal.profiles()
        peers = e.worlds.peers
        tags = np.tile(engine.fiscal.power_tags(), peers.n // e.worlds.powers)
        self.assertTrue((peers.tech_at["central_banking"][tags == "GBR"] <= 2).all())
        for simulated, countries in [(e, p["tag"][0, e.fiscal_ranks[0]]), (peers, tags)]:
            for i, tag in enumerate(countries):
                for tech, (earliest, latest) in engine.fiscal.research_bounds()[tag].items():
                    at = simulated.tech_at[tech][i]
                    self.assertLessEqual(earliest, at, (tag, tech))
                    self.assertLessEqual(at, latest, (tag, tech))

    def test_a_calm_good_keeps_its_label_inside_the_buffer(self):
        e = self.economy()
        h = np.full_like(e.h, engine.g.RISING_HYPE)
        e.word[:] = engine.levers.CALM_WORD
        self.assertEqual(e.goods_words(h)[0, 0], engine.levers.CALM_WORD)
        e.word[:] = 0
        self.assertEqual(e.goods_words(h)[0, 0], engine.levers.CALM_WORD + 1)

    def test_encouragement_lifts_when_a_boom_can_bust(self):
        e = self.economy("passive")
        e.peak[0, 0] = max(p for _, p, *_ in engine.g.UNWINDS) * 2
        e.lever[0, 0] = 1
        e.step()
        self.assertEqual(e.lever[0, 0], 0)

    def test_player_goods_orders_observe_grace_and_restart_the_three_pulse_wait(self):
        cfg = engine.defaults()
        cfg["inputs"].update(fiscal_profiles=0, goods=[24, 24], ai_authority=[50, 50], boom_rate=[0, 0])
        e = engine.Economies(engine.current(), cfg, "passive", 1, 7)
        good = engine.g.GOODS[e.goods_ids[0, 0]]
        cfg["player_lever_orders"] = [f"{day} {good} encourage" for day in (
            "1836-01-28", "1836-02-03", "1836-02-05", "1836-03-02", "1836-04-02", "1836-05-02", "1836-05-09")]
        e = engine.Economies(engine.current(), cfg, "passive", 1, 7)
        for expected, wait in [(1, 3), (0, 3), (0, 2), (0, 1), (1, 3)]:
            e.step()
            self.assertEqual((e.lever[0, 0], e.lever_wait[0, 0]), (expected, wait))

    def test_batch_matches_individual_candidate_worlds(self):
        cfg = engine.defaults()
        cfg["inputs"]["years"] = 2
        values = [{"LEV_SAFE": 2}, {"LEV_SAFE": 4}]
        packed = engine.batch(([0, 1], "ai", values, cfg, 4, 7))
        for i, candidate in enumerate(values):
            single = engine.job((i, "ai", candidate, cfg, 4, 7))
            self.assertEqual(single[2:], packed[i][2:])
