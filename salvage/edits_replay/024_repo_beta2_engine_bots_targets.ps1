cd G:\GameDev\speculative-markets
Get-Content tools\generate.py | Select -Skip 1764 -First 22; Get-Content tools\generate.py | Select -Skip 1354 -First 24
$p="C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad\beta2_engine.py"
@'
from pathlib import Path
R=Path(r'G:\GameDev\speculative-markets\tools\tuner')
def ed(f,*pairs):
    p=R/f; s=p.read_bytes().decode('utf-8'); nl='\r\n' if '\r\n' in s else '\n'; s=s.replace('\r\n','\n')
    for a,b in pairs:
        assert s.count(a)==1,(f,s.count(a),a[:90]); s=s.replace(a,b)
    p.write_bytes(s.replace('\n',nl).encode('utf-8'))
ed('engine.py',
('    ("AI_TIGHT", credit_ai, "AI_TIGHT", "AI", "AI tightens above"),\n',''.join(f'    ("{k}", credit_ai, "{k}", "AI", "{t}"),\n' for k,t in (("AI_MARGIN","AI tightens this close to a panic"),("AI_MARGIN_BACK","AI leaves Tight this far from a panic"),("AI_MARGIN_LOOSE","AI goes Loose this far from a panic"),("AI_MARGIN_FROM","Margin counts from this leverage"),("AI_MARGIN_LEAN","Margin moved by this share of the lean"),("AI_LOOSE_ROOM","AI goes Loose this far under its limit")))),
('    ("AI_LEV_BACK", lv, "AI_LEV_BACK", "AI", "AI loosens below this share of its limit"),\n',''),
('''    # borrows as the Balanced AI does, but goes Tight while the Panic Risk alert shows''','''    # the risk ladder: one technique (Loose while the margin over the Panic Threshold allows, Tight on danger and while Bad Debts
    # last, rescue, buy up large Bad Debts), so only the leverage they let run differs (Economies.plan)
    "cut4": dict(plan=dict(hi=4, lo=3, c_in=72, c_out=60), rescue=1, bailout=1, bailout_from=10, mania=(1, 0, 0), afford=False),
    "hold6": dict(plan=dict(hi=6, lo=5, m_in=10, m_out=14, loose_lev=5.5, loose_m=13), rescue=1, bailout=1, bailout_from=10, mania=(1, 0, 0), afford=False),
    # up to 10 months, then Tight all the way down to 4; out early as the Panic Threshold nears
    "run10": dict(plan=dict(hi=10, lo=4, m_in=8, m_out=12, loose_lev=9.5, loose_m=11), rescue=1, bailout=1, bailout_from=10, mania=(1, 0, 0), afford=False),
    # the same run, watching nothing but leverage
    "blind10": dict(plan=dict(hi=10, lo=4, loose_lev=9.5, loose_m=-99), rescue=1, bailout=1, bailout_from=10, mania=(1, 0, 0), afford=False),
    # borrows as the Balanced AI does, but goes Tight while the Panic Risk alert shows'''),
('''    loose = K["WARY"] if K.get("AI_LOOSE") is None else K["AI_LOOSE"]
    return dict(tight_conf=K["AI_TIGHT"] + lean, tight_lev=lim,
                untight_conf=np.maximum(K["AI_TIGHT"] - 1 + lean, K["CONF_START"] + 3), untight_lev=lim,
                loose_conf=loose + lean, loose_lev=lim * K["AI_LEV_BACK"],
''','''    loose = K["WARY"] if K.get("AI_LOOSE") is None else K["AI_LOOSE"]
    return dict(limit=lim, lean=lean, loose_conf=loose + lean,  # loose_conf and unloose_conf: the levers' (ai_levers)
'''),
('''        fever = self.fever if is_ai else np.zeros(n, bool)
        to_tight = can & (self.stance != -1) & ((self.conf > P["tight_conf"]) | (lev > P["tight_lev"])) & ~fever
        to_normal_t = can & (self.stance == -1) & (self.conf < P["untight_conf"]) & (lev < P["untight_lev"])
        to_loose = can & (self.stance == 0) & (self.conf < P["loose_conf"]) & (lev < P["loose_lev"]) & ~self.in_panic
        to_normal_l = can & (self.stance == 1) & ((self.conf >= P["unloose_conf"]) | self.in_panic)
        if P.get("timing"):''','''        fever = self.fever if is_ai else np.zeros(n, bool)
        want = self.desired_credit
        if "limit" in P:  # the AI's rule (credit_ai.STANCE)
            margin, bad = self.conf - self.panic_at(lev) + K["AI_MARGIN_LEAN"] * P["lean"], self.crunch > 0
            near = (lev >= K["AI_MARGIN_FROM"]) & (margin < K["AI_MARGIN"])
            to_tight = can & (self.stance != -1) & ((lev >= P["limit"]) | bad | near) & ~fever
            out = (self.stance == -1) & (lev < P["limit"]) & ~bad & ((lev < K["AI_MARGIN_FROM"]) | (margin >= K["AI_MARGIN_BACK"]))
            loose = (margin > K["AI_MARGIN_LOOSE"]) & (lev < P["limit"] - K["AI_LOOSE_ROOM"]) & ~self.in_panic
            to_loose = can & ((self.stance == 0) | out) & loose
            to_normal_t, to_normal_l = can & out & ~loose, can & (self.stance == 1) & ~loose
        elif "plan" in P:
            want = self.plan(P["plan"], lev)
        else:
            to_tight = can & (self.stance != -1) & ((self.conf > P["tight_conf"]) | (lev > P["tight_lev"])) & ~fever
            to_normal_t = can & (self.stance == -1) & (self.conf < P["untight_conf"]) & (lev < P["untight_lev"])
            to_loose = can & (self.stance == 0) & (self.conf < P["loose_conf"]) & (lev < P["loose_lev"]) & ~self.in_panic
            to_normal_l = can & (self.stance == 1) & ((self.conf >= P["unloose_conf"]) | self.in_panic)
        if P.get("timing"):'''),
('''            to_normal_t &= ~risky
        elif not is_ai:''','''            to_normal_t &= ~risky
            to_loose &= ~risky
        elif not is_ai and "plan" not in P:'''),
('''        new = _first([to_tight, to_normal_t, to_loose, to_normal_l], [-1, 0, 1, 0], self.stance)
        if self.desired_credit is not None:
            new = np.where(can, self.desired_credit, self.stance)
''','''        new = np.where(can, want, self.stance) if want is not None else _first([to_tight, to_normal_t, to_loose, to_normal_l], [-1, 0, 1, 0], self.stance)
'''),
('''    def decide(self):
        """After the pulse:''','''    def plan(self, p, lev):
        """The risk ladder's players: the stance they want, from what a player sees (confidence, Panic Threshold, leverage, Bad Debts)."""
        margin, on = self.conf - self.panic_at(lev), lev >= 4
        go = (lev >= p["hi"]) | (on & (margin < p.get("m_in", -INF))) | ((self.conf > p.get("c_in", INF)) & (lev >= 2)) | (self.crunch > 0)
        back = (lev <= p["lo"]) & ((margin >= p.get("m_out", -INF)) | ~on) & (self.conf < p.get("c_out", INF)) & ~go
        self.paying = np.where(go, True, np.where(back, False, self.paying))
        loose = (lev < p.get("loose_lev", -INF)) & (margin > p.get("loose_m", INF)) & (self.conf >= (25 if "m_in" in p else 0)) & ~self.in_panic
        return np.where(self.paying, -1, np.where(loose, 1, 0))

    def decide(self):
        """After the pulse:'''),
('''"late_panic_months", "pledge_months", "pledge_rescues", "distrust_late_months", "gap_end")}
''','''"late_panic_months", "pledge_months", "pledge_rescues", "distrust_late_months", "gap_end",
                                           "growth_ln", "lev8_months", "runs10", "runs10_out", "runs10_burnt")}
        self.paying, self.run10, self.lev_prev = f.copy(), f.copy(), z.copy()  # plan's Tight, a run-up past 9.5 months not yet over, last month's leverage
'''),
('''        gap = self.gdp / self.gdp_base - 1
        s["gdp_gap_sum"] += gap
''','''        # a run-up: leverage crosses 9.5 months; burnt if a panic starts before it is back under 5, out if not
        s["lev8_months"] += lev4 >= 8
        up = ~self.run10 & (self.lev_prev < 9.5) & (lev4 >= 9.5) & ~start
        burnt, off = (self.run10 | up) & start, (self.run10 | up) & ~start & (lev4 < 5)
        s["runs10"] += up
        s["runs10_burnt"] += burnt
        s["runs10_out"] += off
        self.run10, self.lev_prev = (self.run10 | up) & ~burnt & ~off, lev4
        # log growth against no market, the bonus averaged over the run, less what a panic costs the treasury (growth_core)
        cost = self.in_panic * (PANIC_RELIEF + np.where(self.funded_rescue, K["RESCUE_CUT"], 1.0) * PANIC_TAX)
        s["growth_ln"] += (self.I["inv_growth"] / 12 * self.pool_share * self.pool_base_x * (self.pool_inv - 1) + self.I["con_growth"] / 12 * self.build
                           + np.log(np.maximum(1 + self.I["e_gdp"] * self.tp, 0.05)) / self.months - MONEY_GROWTH * cost / 12)
        gap = self.gdp / self.gdp_base - 1
        s["gdp_gap_sum"] += gap
'''),
('''SNAP = 6  # months between''','''def beaten(res):
    """Across one candidate's players: the share of worlds where careful play does better, on the same draws (beaten_pct)."""
    core = {b: r.pop("_core", None) for b, r in res.items()}
    for b, r in res.items():
        if core.get("careful") is not None and core[b] is not None and b != "careful":
            r["beaten_pct"] = {"mean": float((core[b] < core["careful"]).mean() * 100)}


SNAP = 6  # months between'''),
('''    "distrust_late_pct": ("Months with the Exchange Distrusted, 1866 on", "%"),
}
''','''    "distrust_late_pct": ("Months with the Exchange Distrusted, 1866 on", "%"),
    "growth_core": ("GDP growth a year against no market, averaged over the century", "points"),
    "lev8_pct": ("Months with leverage of 8 or more", "%"), "runs10_per_century": ("Run-ups to 10 months a century", ""),
    "runs10_out_pct": ("Run-ups to 10 months that get out", "%"), "beaten_pct": ("Worlds where careful play does better", "%"),
}
# growth_core: treasury money spent costs growth too. MONEY_GROWTH: growth per unit of GDP spent; a panic year's relief and lost taxes,
# shares of GDP (both not in the engine's growth path)
MONEY_GROWTH, PANIC_RELIEF, PANIC_TAX = 0.35, 0.04, 0.15 * 0.15
'''),
('''        "trust_top_pct": s["trust_top_months"] / T * 100,
        "low_pct"''','''        "trust_top_pct": s["trust_top_months"] / T * 100,
        "growth_core": (np.exp((s["growth_ln"] - MONEY_GROWTH * spend / 100) / (T / 12)) - 1) * 100,
        "lev8_pct": s["lev8_months"] / T * 100, "runs10_per_century": s["runs10"] * cent,
        "low_pct"'''),
('''    out["frozen_pct"] = {"mean"''','''    out["runs10_out_pct"] = {"mean": float(s["runs10_out"].sum() / max((s["runs10_out"] + s["runs10_burnt"]).sum(), 1) * 100)}
    out["_core"] = per["growth_core"]
    out["frozen_pct"] = {"mean"'''),
)
ed('lab.py',('''                res = {b: s for b, (s, _) in got[cid].items()}
''','''                res = {b: s for b, (s, _) in got[cid].items()}
                engine.beaten(res)
'''))
T=[("panics_per_century","passive",5.5,4,7,"A country that never touches the levers panics about as often as the 19th century's large economies did."),
("panic_months_pct","passive",1.5,.8,3,"Panics are sharp events, not a permanent state."),
("panic_length","passive",4.5,3,6,"A panic lasts a season or two, as the historical ones did."),
("mania_pct","passive",7,5,10,"Manias are part of the century: about seven months in each ten years without a hand on the levers."),
("mania_to_panic_pct","passive",35,25,50,"Many Manias end in a panic, as 1825, 1837, 1847, 1857, 1873 and 1890 did; the rest cool off."),
("growth_core","passive",.08,0,.15,"A country that leaves the market alone still grows a little faster with it than without it."),
("bad_spell","passive",18,9,30,"Left alone, Bad Debts clear in a year or two."),
("late_panic_pct","passive",3.5,1,6,"More advanced finance brings more crashes late in the century, but never a world in constant crisis."),
("panic_output_loss","passive",17,10,25,"A hands-off country pays for the leverage it let build, as the long slump after 1873 did."),
("low_pct","passive",12,5,25,"Confidence stays low for a while after a crash: the Wary tier is part of the cycle."),
("up_pct","passive",42,25,55,"Good years are common but not the norm."),
("trust_top_pct","passive",75,50,90,"The Exchange is usually Respected or Trusted, and losing that means something."),
("growth_core","careful",.27,.2,.35,"Careful play pays, safely."),
("panics_per_century","careful",2,1,3.5,"Even careful play meets a panic or two a century."),
("trust_top_pct","careful",85,65,100,"Careful play keeps the Exchange Respected or better almost all the time."),
("growth_core","run10-careful",.2,.1,.3,"Running leverage up to 10 months and getting out pays better than careful play."),
("growth_core","run10-hold6",.05,-.1,.2,"And no safe middle style makes the run-up pointless."),
("runs10_per_century","run10",3,1.5,5,"A player who goes for it reaches 10 months a few times a century."),
("runs10_out_pct","run10",65,50,80,"Most run-ups get out unscathed, and a good share do not."),
("panics_per_century","run10",4,3,5.5,"The run-up is the riskier way to play."),
("lev8_pct","run10",8,4,20,"High leverage is somewhere a player spends time."),
("beaten_pct","run10",22,10,35,"The risk is real: in some worlds careful play does better."),
("mania_pct","run10",4,2,8,"A player riding leverage meets Manias."),
("growth_core","blind10-careful",.02,-.1,.15,"Running up without watching the Panic Threshold is worth about what careful play is."),
("growth_core","reckless",-.1,-.4,.05,"Reckless play throws the gains away."),
("growth_core","ai",.35,.2,.5,"AI countries use leverage, so rivals stay competitive."),
("panics_per_century","ai",4,3,6,"AI countries panic about as history did, so Great Powers meet crises and the Long Depression can start."),
("mania_pct","ai",3.5,2,6,"AI countries have Manias too."),
("trust_top_pct","ai",85,50,100,"AI Exchanges are usually Respected or Trusted."),
("rescue_share","ai",35,20,60,"Some AI governments rescue their banks and some let the panic run.")]
import json
(R/'targets.json').write_text("[\n"+",\n".join(" "+json.dumps({"metric":m,"who":w,"aim":float(a),"lo":float(l),"hi":float(h),"weight":1.0,"why":y}) for m,w,a,l,h,y in T)+"\n]\n",encoding='utf-8',newline='\n')
'@ | Set-Content -Encoding utf8 $p
py -3 -B $p
$env:SPEC_MOD_OUT="$pwd\build_scratch\rc_1.3.1"; py -3 -B tools/generate.py 2>&1 | Select-Object -Last 3; py -3 -B tools/check.py 2>&1 | Select-Object -Last 2
py -3 -B tools/credit_ai.py | Select -Last 2; py -3 -B tools/tuner/engine.py 2>&1 | Select-Object -Last 16; py -3 -B tools/leverage.py 2>&1 | Select -Last 4
