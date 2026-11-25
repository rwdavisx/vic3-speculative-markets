# Handoff: tuner session, 1.3.0 release to 1.3.1-beta.4/5 (salvaged 2026-11-25)

Source session: `session_012vW2ozPoKWS1pbZpKWRHvh` ("Tuner session upload approval"). It worked on the user's Windows desktop in `G:\GameDev\speculative-markets`, branch `release-1.1`. It died at **2026-11-25 13:12 UTC** when the desktop became unreachable. Its last command was a scan running in the foreground, and the result never came back.

- **Last commit:** `25020bb` "1.3.0 release" (2026-11-24 20:21:52 UTC), pushed to `origin/release-1.1`.
- **After that commit:** everything below is uncommitted on the desktop. Nothing after 25020bb was committed or pushed.
- **Exact replay material:** `salvage/edits_replay/`. Its `INDEX.md` lists every file-changing command in order, with outcomes.
- **Sources:** this note comes from the transcript only. Desktop files were not inspected. Items marked *uncertain* could not be confirmed from the transcript.

Scratch locations on the desktop that matter:
- `$s` = `C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad`. It holds the scan scripts `r12b.py`, `mania12.py`, `mania12_h.py`, `l0.json`, `g1.json`, `g2.json`, `g3.json` and others. It is in Windows temp, so copy it out before it is cleaned.
- `G:\GameDev\_claude_scratch\tune_fresh\` holds the independent subagent study (hunt.py, lists.py, best.py, ai2.py, confirm.py, heigh*.py, outputs).
- `G:\GameDev\_claude_scratch\v130\` holds the infographic, infographic131, ridesim and waterworks.html.

---

## 1. Chronology: what the user asked and decided

All times are UTC. User messages are quoted verbatim.

### Before the commit (context)
| Time | User | Outcome |
|---|---|---|
| 11-24 19:04 | "Yes fix it.. and I'm trying to decide on pushing the rest.. should I just do 1.2.2 for everything we have done or 1.3" | Became 1.3 |
| 19:23 | "do the translations" | |
| 19:25 | "actuall a lot of the actions for contests tooltips are overly verbose.. i also feel like the calculator style tooltip isnt in place for the contest bar either.. like liberty desire.. use it as an example" | |
| 19:27 | "should we add the actual lending standards number and display it similarly with the number (x.x) type format? so people can visually see how its actually moving?" | |
| 19:32 | "also for the sub tooltips of industries effecting construction efficiency.. can we add the relevant good and investor interest icons to the tooltip? instead of it just being text" | |
| 19:46 | "I think we are ready to push 1.3 when you complete this update" | |
| 19:51 | "can you also update the offline simulation artifact? and we might need a new infographic showcasing types of country growth / performance / bonuses" | |
| ~20:17 | (assistant) | 1.3 published to Steam: stable 1.3.0, Beta 1.3.0-beta.1, Morgenroete 1.3.0, TechRes 1.2.0, BPM 1.1.0, CMF description only |
| 20:21 | "Yes" (commit and push, and add the infographic) | Commit 25020bb pushed. Infographic renamed "Skilled" to "Balanced" and sent to the user to upload to imgur |

### After the commit
| Time | User (verbatim) | What the session did |
|---|---|---|
| 20:23 | (no message) | Published the tutorial page update to the existing artifact https://claude.ai/artifact/RK4Lrf6U1rU7HC8Vx5pDvy (version 12, now on 1.3). Asked the user for an imgur link for the infographic. |
| 20:36 | "hold on why is careful better than skilled? and why is reckless money bag green" | Explained that Skilled was going Tight at 6 rather than 4. Swapped the Reckless icon from mod_loose to event_mania, relabelled rows "leverage to 4/6", and resent the PNG. |
| 20:41 | "i dont understand.. i thought a skilled player could run up to 10-12 months of leverage and get a nice reweard but tighten up and get out unscathed from time to time.. and that to me is more risky and better than careful cutting back at 4" | Built ridesim experiments. Found that 1.3 allows no way out: payoff under 1% a month, and the panic line passes normal confidence at about 7 months. |
| 20:49 | "it seems like countries also dont spend as much time in mania as they should" | Agreed: hands-off Mania was about 1% of months against a 4% target. |
| 20:50 | "helloo?" | |
| 20:56 | "status" | |
| 21:05 | (assistant proposal) | Tight payoff 0.95% to 10%, FIN_BOOM_BASE 1 to 1.5, LEV_PANIC_SPAN 55 to 50. Infographic upload put on hold. |
| 21:07 | "yes build it as 1.3.1-beta" | Built **1.3.1-beta.1** (not uploaded). |
| 21:28 | "use a subagent to figure out how to best tune everything. im afraid your context is clouding your judgement. it needs to look at all of the mechancis we have in game and figure it out the best targets to tune toward and best way to tune.. we have the infrastructure set up im just afraid our current session has clouded biased opinions and is missing the best tuning still.. like how you are saying ai wont borrow max credit leverage even though they could strategically do that to get out ahead.. it sounds like it was never tuned like that" | Launched a fresh-eyes subagent working in `_claude_scratch\tune_fresh`. Beta upload held. |
| 22:34 | "Status?" | Subagent still running. |
| 23:14 | (subagent report) | Recommended the "K5" values, a margin-based AI rule and new targets (section 2). The session spot-checked and reproduced them. |
| 23:18 | (assistant) | Asked: "Should I build it and replace the targets?" |
| 11-25 00:17 | "Yes" | Built **1.3.1-beta.2** with K5, the new AI rule and the new targets.json. Saved a memory note. |
| 02:01 | "Yes. Push beta 2.. I'm wondering.. what are the main differences in layman terms from the current stable version" | **Uploaded beta.2** to the Beta Workshop item; Steam confirmed. Gave a plain-language comparison. |
| 02:10 | "You said it meets 29 of 30 targets?" | Confirmed 29, 30 and 30 on seeds 9001 to 9003. Cautioned that the targets and values came from the same exercise, steady 6 still beats the run-up, and the AI is too strong. |
| 02:17 | "Can we make mania more common?" | Recommended FIN_BOOM_BASE 1.75 to 2.0. |
| 04:41 | "Yes" | Built **beta.3** (boom 2.0, Heightened heat 75 to 78). Not uploaded at first. |
| 05:46 | "why is this one better than the stable 1.3" | Gave a like-for-like simulator comparison. |
| 05:57 | "yea do you want to test it?" | Ran a headless AI-only game from 1836 to 1866. It was clean at 1838, then **beta.3 was uploaded** (06:03, Steam confirmed). The game finished at 06:34 with no crash, but Mania was about one third of the simulator's figure. |
| 06:13 | "Status" | Gave interim numbers. |
| 11:02 | "Yes" (correct the simulator, then pick a boom size) | Recalibrated the simulator against the beta.3 and 1.2.2 games. Recommended boom 2.1 and LEV_PANIC_SPAN 35 to 30. |
| 11:34 | "Yes.. and you can change whatever you want if it brings us more in line with our desired behavior" | Started a wide search (b4.py). |
| 11:35 | "I want a run up to 12" | |
| 11:35 | "I said 10 to 12 and you have taken that to mean 10" | Stopped the search. Added `run12` and `blind12` bots, updated the memory note, and retuned for 12. |
| 11:57 | "Status" | No text reply. The session kept working: killed scan5 and added knobs. |
| 12:13 | "Status" | No text reply. Scans continued. |
| 12:49 | (assistant) | **beta.4 built and staged, NOT uploaded.** Asked "Shall I upload beta.4…?" |
| 12:53 | "So are you saying credit lent levels via tech are now 3/10/11/12?" | |
| 12:53 | "Should probably be 3/6/9/12" | |
| 12:58 | (assistant) | Admitted 3/10/11/12 was a mistake and compared it with 3/8/10/12. Then wrote "Setting it to 3/6/9/12, even steps of 3 per tech, and retuning the risk around it." Set `LEV_LADDER` to [3,6,9,12] in tuning.json and started scanning. |
| 13:06 | (assistant) | "The higher ladder needs more bite for reckless play. Second scan aims there." |
| 13:12 | (died) | A third scan (4 candidates, 3 seeds) was running. No result was recorded. |

**Standing owner rules restated in this session** (from the subagent prompt and memory):
- Leverage is high risk, high reward.
- Punish reckless play by scaling with leverage. No hard caps on penalties. The session declined CONF_CRASH_MAX 35 to 25 for this reason.
- Tight credit is a full stop on new lending.
- There are only three credit settings.
- Leverage rising over the century with tech is intended.
- Use round values.
- Keep it simple.
- State every balance change as old → new.

At 11:34 the user also allowed "change whatever you want if it brings us more in line with our desired behavior". Changes must still be named.

---

## 2. The independent subagent study (23:14, summary)

The full report is in the transcript at 2026-11-24 23:14. The scripts are in `_claude_scratch\tune_fresh\`. REPORT.md was not written because the harness refused it.

**Findings:**
- In 1.3.0 and beta.1, leverage above about 6 months loses. No bot ever went to 10 and back.
- The AI went Tight above confidence 80 or at a fixed leverage limit, and ignored the panic margin.
- Sound Credit is about 75% of the reward and counts leverage-months linearly.
- The income floor (0.9% of GDP) binds for 84–96% of countries.
- The old `growth_edge` barely charges for rescues. It was replaced by `growth_core`.
- `lab.py check KEY=v` can print the baseline under the new label. Read `latest.json` instead.

**Recommended values "K5"** (adopted in beta.2):

| Key | 1.3.0 | beta.1 | K5 |
|---|---|---|---|
| LEV_PANIC_SPAN | 55 | 50 | 35 |
| FIN_BOOM_BASE | 1.0 | 1.5 | 1.75 |
| LEV_INCOME_FLOOR | 0.009 | 0.009 | 0.007 |
| LEV_RECORD_GAIN | 0.01 | 0.01 | 0.02 |
| LEV_CRUNCH_BUILD | 0.05 | 0.05 | 0.06 |
| CREDIT_RUNOFF_TIGHT | (0.0095) | 0.1 | 0.1 |
| Heightened rule | heat 70, boom 1.1 | same | heat 75, boom 1.0 |

**New AI rule** (adopted in beta.2 as `credit_ai.STANCE`):
- Go Tight when leverage ≥ AI_MARGIN_FROM (4) and the margin (confidence − panic_at + 0.6 × lean) < AI_MARGIN (10), or at the leverage limit, or while Bad Debts remain.
- Leave Tight at a margin ≥ 16.
- Go Loose at a margin > 15 while leverage is below the limit − 0.5.

**New targets:** a 30-row "risk ladder" set with bots cut4, hold6, run10, blind10 and metric growth_core. It replaced targets.json in beta.2.

**What K5 could not fix:** steady 6 still beat a run-up to 10 (0.45 against 0.37). Simulator growth is probably overstated about 2x.

---

## 3. Parameter history (tools/tuning.json and generator constants)

Notes for the table:
- "default" means the key is absent from tuning.json and the generator default applies.
- `LEV_LADDER` default is (3, 8, 10, 12), from leverage.py.
- `LOOSE_CREDIT` was hard-coded at 1.6 in generate.py `STANCE_CREDIT` until 11:58.
- `LEV_RECORD_PAST` and `LEV_RECORD_FROM` (default 6) are new knobs added at 12:05.

| Key | 1.3.0 (stable, 25020bb) | beta.1 (built, never uploaded) | beta.2 (uploaded 02:01) | beta.3 (uploaded 06:03, **live Beta**) | beta.4 (built 12:48, **NOT uploaded**) | Desktop state at death (13:12) |
|---|---|---|---|---|---|---|
| CREDIT_RUNOFF_TIGHT | — (0.0095) | **0.1** | 0.1 | 0.1 | 0.1 | 0.1 |
| FIN_BOOM_BASE | 1.0 | **1.5** | **1.75** | **2.0** | **2.1** | 2.1 |
| LEV_PANIC_SPAN | 55 | **50** | **35** | 35 | **25** | 25 (under retune) |
| LEV_INCOME_FLOOR | 0.009 | 0.009 | **0.007** | 0.007 | **0.006** | 0.006 (under retune) |
| LEV_RECORD_GAIN | 0.01 | 0.01 | **0.02** | 0.02 | 0.02 | 0.02 |
| LEV_CRUNCH_BUILD | 0.05 | 0.05 | **0.06** | 0.06 | **0.05** | 0.05 |
| LEV_CRUNCH_FADE | 0.35 | 0.35 | 0.35 | 0.35 | 0.35 (explicitly set) | 0.35 (under retune) |
| BUST_PER_HYPE | default 2.5 | 2.5 | 2.5 | 2.5 | **1.5** | 1.5 (under retune) |
| LEV_LADDER | default [3,8,10,12] | default | default | default | **[3,10,11,12]** | **[3,6,9,12]** (set 12:58, never built) |
| LOOSE_CREDIT (Loose lending multiplier) | 1.6 (hard-coded) | 1.6 | 1.6 | 1.6 | **2.5** (new knob) | 2.5 |
| LEV_RECORD_PAST (extra weight per month past 6) | n/a | n/a | n/a | n/a (0) | **2** (Sound Credit 1.67% to 5% per month past 6) | 2 (under retune) |
| AI_LEV_LIMIT (Cautious/Balanced/Bold) | 5 / 8 / 9.5 | same | **6.5 / 8 / 9.5** (leverage.py default) | same | **8 / 9.5 / 11.5** (in tuning.json) | 8 / 9.5 / 11.5 |
| AI credit rule | AI_TIGHT 80 + fixed limits | same | **margin rule** (AI_MARGIN 10, _BACK 16, _LOOSE 15, _FROM 4, _LEAN 0.6, AI_LOOSE_ROOM 0.5) | same | same | same |
| Heightened volatility (generate.py VOLATILITY) | heat 70, per 0.25, boom 1.1 | same | **heat 75, boom 1** | **heat 78**, boom 1 | 78 / 1 | 78 / 1 |
| generate.py VERSION | 1.3.0 | **1.3.1** | 1.3.1 | 1.3.1 | 1.3.1 | 1.3.1 |

Intermediate values that were tried and **overwritten** in tuning.json:
- 12:23: LEV_PANIC_SPAN 20, LEV_CRUNCH_BUILD 0.1, BUST_PER_HYPE 2.0, LEV_LADDER [3,9,11,12], AI_LEV_SCALE 1.2.
- 12:31: LEV_CRUNCH_FADE 0.2, LEV_RECORD_PAST 1.5.
- 12:35: FADE 0.3, PAST 2.5, SPAN 25, BUST 1.75, FLOOR 0.006.
- 12:43: FADE 0.35, PAST 2, BUST 1.5. These are the beta.4 values.
- `LEV_RECORD_FADE` was added at 11:58 and removed again at 12:23. It did not help.

**Simulator (not game) changes**, all in `tools/tuner/`:
- engine.py PRICE_SPREAD 0.55 → 0.75 and PRICE_COMMON 0.065 → 0.4 (11:08).
- inputs.json: rough_sd [0.5, 0.5], rough_months [6, 6], rough_skew 0, price_sd [0.032, 0.032], plus source note `game_refit_20261125`.

**Exact final beta.4 tuning.json deltas versus beta.3** (from the beta.4 changelog):
- Loose 60% → 150% more lending.
- Ladder 3/8/10/12 → 3/10/11/12.
- Income floor 0.7% → 0.6%.
- Sound Credit past 6 months 1.7% → 5% per month.
- Panic line at 12 months 60 → 50 (span 35 → 25).
- Bust cost 2.5 → 1.5.
- Bad Debts construction 6% → 5% per point.
- Boom 2.0 → 2.1.
- AI Tight limits 6.5/8/9.5 → 8/9.5/11.5.

---

## 4. Simulator results

Column abbreviations: careful = cut at 4. hold6 = steady 6. run10 / run12 = run-up to 10 or 12 and then out. blind = run-up without watching the panic line. "12-C" = run12 − careful. "12-6" = run12 − hold6. pan12 = run12 panics per century. ups = run-ups per century. out = % of run-ups that escape. beat = % of worlds where careful wins. lev8 = % of months at 8+ leverage. mania P / 12 / AI = % of months in Mania. Growth is `growth_core`, in GDP-growth points a year.

### 4a. 1.3 → beta.1 (old simulator, 21:05–21:18, 1,000 centuries)
| Style | 1.3 | beta.1 |
|---|---|---|
| Careful (to 4) | +0.31 | +0.25 |
| Balanced (to 6) | +0.26 | +0.30 |
| AI | +0.17 | +0.25 |
| Hands-off | +0.10 | +0.10 |
| Reckless | +0.07 | +0.07 |
| Mania, hands-off | 1% | 3% |
| AI panics a century | 5.5 | 3.7 |

### 4b. Subagent / session rerun of K5 (23:18, 500 economies, old simulator)
| | 1.3 | beta.1 | K5 (beta.2) |
|---|---|---|---|
| Careful | 0.29 | 0.24 | 0.24 |
| Cut at 4 | 0.29 | 0.26 | 0.27 |
| Steady 6 | 0.20 | 0.35 | 0.45 |
| Run to 10 and out | 0.14 | 0.27 | 0.37 |
| Blind run to 10 | 0.06 | 0.12 | 0.27 |
| Reckless | -0.03 | -0.03 | 0.01 |
| Run-ups a century | 0.1 | 0.3 | 1.9 |
| Escape | 0% | 31% | 64% |
| Mania, hands-off | 0.9% | 2.8% | 5.1% |

AI under K5: old rule 0.34 growth, 2.6 panics. New rule 0.45 growth, 3.4 panics.

### 4c. beta.2 target check (02:12, seeds 9001–9003, old simulator)
- Targets met: 29, 30 and 30 of 30. Careful panics 0.95–1.01 (target ≥ 1).
- run10 − careful: +0.12. run10 − hold6: -0.08. Run-ups: 1.8–2.1 a century.
- Mania, hands-off: 5.0–5.3%. AI growth: 0.44–0.46.

### 4d. Mania options (02:33, old simulator)
| Mania % | beta.2 (1.75) | 2.0 | 2.25 | 2.5 |
|---|---|---|---|---|
| Hands-off | 5.1 | 8.4 | 12.8 | 18.7 |
| Run to 10 | 2.7 | 5.8 | 10.4 | 16.8 |
| Steady 6 | 1.9 | 4.5 | 8.6 | 14.4 |
| AI | 2.5 | 5.3 | 9.4 | 15.4 |
| Careful | 0.1 | 0.4 | 1.0 | 2.3 |

### 4e. beta.3 vs stable (05:50, old simulator, 3,000 economies)
| Measure | Stable 1.3 | beta.3 |
|---|---|---|
| run10 − careful | -0.15 | +0.14 |
| Escape | 1% | 64% |
| Run-ups | 0.15 | 2.1 |
| Careful better | 72% | 17% |
| Mania P / run10 / AI | 0.9 / 0.2 / 0.5% | 8.4 / 5.8 / 5.3% |
| AI leverage | 3.4 | 4.4 |
| AI panics | 5.2 | 3.5 |
| Careful / hold6 / run10 / reckless growth | 0.29 / 0.20 / 0.14 / -0.04 | 0.22 / 0.45 / 0.37 / 0.01 |

### 4f. Real headless game, beta.3, AI-only 1836–1866 (06:35)
Run folder: `runs\sweep_beta3\beta3_01`. About 35 largest economies.

| Measure | 1.2.2 game | beta.3 game | Simulator (old) |
|---|---|---|---|
| Months in Mania | 0.2% | 0.7% | 2.4% |
| Mania, 1856–66 | 0.5% | 1.8% | 2.75% |
| Countries with a Mania | 4/35 | 13/35 | – |
| Months at 70+ confidence | 2% | 26% | 29% |
| Average leverage | 2.9 | 3.4 | 3.8 |
| Time Loose | 1% | 29% | – |
| Panics per 100 years | 2.0 | 3.1 | 1.9 |

AIs reached 8+ leverage 17 times: 6 got out, 7 panicked, 4 were unresolved. The game loaded clean, with no new mod errors and no crash.

### 4g. Corrected simulator (11:19), beta.3 vs options
After correction: game Mania 0.7% vs simulator 0.8%. Months at 75+: 7.4% vs 6.3%. Panics: 3.3 vs 2.7.

| | beta.3 | Boom 2.1 | Boom 2.1 + span 30 |
|---|---|---|---|
| Mania P / AI | 5.7 / 3.2% | 7.0 / 4.4% | 6.8 / 4.2% |
| run10 − careful | +0.09 | +0.10 | +0.13 |
| Escape | 59% | 58% | 66% |
| Run-up panics | 6.8 | 6.9 | 6.4 |
| AI panics | 4.6 | 4.7 | 4.1 |
| Targets met | 26–27 | 27 | 29 |

### 4h. Run to 12 under beta.3 values (11:46, corrected simulator, 500 economies)
| Bot | Growth | vs careful | vs hold6 | Panics | Mania | Run-ups | Out | Beaten |
|---|---|---|---|---|---|---|---|---|
| careful | 0.22 | — | -0.17 | 2.0 | 0.1 | 0 | | |
| hold6 | 0.39 | +0.17 | — | 5.3 | 2.1 | 0 | | 4% |
| run10 | 0.31 | +0.09 | -0.08 | 7.0 | 3.0 | 1.66 | 61% | 24% |
| run12 | 0.29 | +0.07 | -0.10 | 7.2 | 3.2 | 0.42 | 50% | 26% |
| blind12 | 0.20 | -0.01 | -0.18 | 8.8 | 3.7 | 0.67 | 45% | 47% |
| reckless | -0.00 | -0.22 | | 9.6 | 7.4 | | | 64% |
| ai | 0.44 | +0.22 | +0.05 | 4.7 | 3.2 | | | |
| passive | 0.08 | -0.14 | | 6.0 | 6.0 | | | |

### 4i. beta.4 final (12:35–12:49, corrected simulator, 1,000 economies, seeds 1–3/4)
- Growth: careful 0.22–0.23, hold6 0.48–0.50, run10 0.54–0.55, run12 0.50–0.51, blind12 0.44–0.45, reckless -0.07–0.02, ai 0.66–0.68, passive 0.17–0.23.
- run12 vs others: 12-C +0.27–0.29, 12-6 +0.02–0.03.
- Risk: pan12 5.8–6.5, ups 1.6–1.8, out 62–64%, beat 10–12%.
- Mania P / 12 / AI: about 7.4–7.9 / 5.4–5.5 / 4.8–5.1.
- Targets met: 25 or 26 of 30. Misses: AI growth 0.67 (target ≤ 0.5); run12 panics about 6 (target ≤ 5.5); blind12 − careful about 0.22 (pays too well); passive growth about 0.20.
- High volatility (78 / 0.25 / 1): hold6 edges run12 by 0.03.
- Message to the user: run12 0.51 against beta.3's 0.29. Reaching 12 happens 1.8 times a century (0.4 before), with 64% escaping.

### 4j. Ladder comparison at beta.4 values (12:55, 800 economies, seeds 1–2)
| | 3/10/11/12 (beta.4) | 3/8/10/12 |
|---|---|---|
| run12 | 0.50–0.52 | 0.54 |
| 12-6 | +0.01–0.03 | +0.04–0.05 |
| 12-C | +0.28–0.29 | +0.31 |
| pan12 | 5.6–6.2 | 5.2–5.7 |
| ups | 1.8–1.9 | 1.3–1.4 |
| Out | 67–68% | 69% |
| Reckless | about 0 | 0.14–0.16 |
| Targets | 26/30 | 22/30 |

The assistant recommended 3/8/10/12 plus more risk and building it as beta.5. The user's simultaneous message asked for **3/6/9/12**, so 3/6/9/12 became the plan.

---

## 5. In-flight work at death: 3/6/9/12 retune

Base for all three scans: beta.4 tuning.json with `LEV_LADDER` = [3,6,9,12]. That ladder value is written to `tools\tuning.json` on the desktop.

Scripts used:
- `$s\r12b.py N SEED list.json` prints growth by bot.
- `$s\mania12.py one N SEED list.json` prints the targets line (`xx/30` plus misses).
- Candidates are deltas applied on top of tuning.json through `lab.sweep`. tuning.json is not rewritten.

### Scan 1 (12:58–13:06, `g1.json`, 800 economies, seed 2)
| Candidate (delta) | careful | hold6 | run12 | blind12 | reckless | ai | passive | 12-C | 12-6 | pan12 | ups | out | beat | lev8 | targets |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| {} (3/6/9/12 base) | 0.23 | 0.50 | 0.52 | 0.49 | **0.22** | 0.64 | 0.25 | +0.29 | +0.02 | 5.1 | 1.42 | 70 | 6 | 8.7 | 24 |
| SPAN25 PAST2 BUST2 | 0.22 | 0.46 | 0.46 | 0.43 | 0.16 | 0.60 | 0.21 | +0.24 | -0.00 | 6.1 | 1.34 | 67 | 10 | 8.0 | 24 |
| SPAN25 PAST3 BUST1.5 | 0.23 | 0.50 | 0.54 | 0.52 | 0.25 | 0.67 | 0.26 | +0.32 | +0.05 | 5.1 | 1.36 | 68 | 5 | 8.7 | 23 |
| SPAN25 PAST3 BUST2 | 0.22 | 0.46 | 0.49 | 0.46 | 0.19 | 0.63 | 0.23 | +0.26 | +0.02 | 6.0 | 1.31 | 65 | 8 | 8.0 | 23 |
| SPAN30 PAST2 BUST1.5 | 0.23 | 0.48 | 0.45 | 0.39 | 0.13 | 0.58 | 0.19 | +0.23 | -0.03 | 5.8 | 1.32 | 61 | 11 | 7.5 | 24 |
| SPAN30 PAST2 BUST2 | 0.22 | 0.45 | 0.40 | 0.33 | 0.08 | 0.55 | 0.16 | +0.18 | -0.05 | 6.8 | 1.24 | 61 | 14 | 6.9 | 25 |
| SPAN30 PAST3 BUST1.5 | 0.23 | 0.48 | 0.47 | 0.42 | 0.15 | 0.60 | 0.20 | +0.25 | -0.01 | 5.8 | 1.27 | 59 | 9 | 7.4 | 23 |
| SPAN30 PAST3 BUST2 | 0.22 | 0.45 | 0.42 | 0.35 | 0.09 | 0.57 | 0.17 | +0.20 | -0.03 | 6.8 | 1.19 | 60 | 13 | 6.8 | 25 |
| SPAN35 PAST2 BUST1.5 | 0.23 | 0.47 | 0.40 | 0.31 | 0.06 | 0.52 | 0.15 | +0.17 | -0.07 | 6.5 | 1.17 | 53 | 16 | 6.4 | 25 |
| SPAN35 PAST2 BUST2 | 0.22 | 0.44 | 0.35 | 0.26 | 0.01 | 0.48 | 0.13 | +0.13 | -0.08 | 7.5 | 1.12 | 51 | 21 | 5.9 | **28** |
| SPAN35 PAST3 BUST1.5 | 0.23 | 0.47 | 0.42 | 0.33 | 0.08 | 0.54 | 0.16 | +0.19 | -0.05 | 6.4 | 1.13 | 52 | 13 | 6.4 | 25 |
| SPAN35 PAST3 BUST2 | 0.22 | 0.44 | 0.37 | 0.28 | 0.03 | 0.51 | 0.13 | +0.15 | -0.06 | 7.4 | 1.08 | 53 | 18 | 5.9 | 27 |
| CRUNCH_BUILD 0.06 | 0.23 | 0.49 | 0.51 | 0.48 | 0.16 | 0.63 | 0.21 | +0.28 | +0.01 | 5.1 | 1.46 | 70 | 8 | 8.8 | 24 |
| INCOME_FLOOR 0.005 | 0.24 | 0.50 | 0.52 | 0.49 | 0.19 | 0.64 | 0.23 | +0.29 | +0.02 | 5.3 | 1.77 | 74 | 7 | 9.5 | 25 |
| INCOME_FLOOR 0.007 | 0.22 | 0.49 | 0.51 | 0.49 | 0.24 | 0.62 | 0.26 | +0.29 | +0.02 | 4.9 | 1.10 | 65 | 4 | 8.0 | 23 |

Notes on scan 1:
- The targets column pairs mania12 lines with candidates by order. The listing has 15 targets lines for 15 candidates; the pairing is in the order printed.
- SPAN35 rows hit 27–28/30 only because their misses shift to run12 panics of 7.4–7.5 and ups of about 1.1. They fail the user's main goal (12-6 negative).
- The assistant concluded: "The higher ladder needs more bite for reckless play." The base has reckless 0.22, almost equal to careful.

### Scan 2 (13:06–13:12, `g2.json`, 800 economies, seed 2)
All candidates use INCOME_FLOOR 0.005.

| Candidate | careful | hold6 | run12 | blind12 | reckless | ai | passive | 12-C | 12-6 | pan12 | ups | out | beat | targets (misses) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SPAN25 PAST3 BUST1.5 FADE0.25 | 0.24 | 0.50 | 0.55 | 0.53 | 0.13 | 0.68 | 0.18 | +0.32 | +0.05 | 5.3 | 1.70 | 73 | 6 | 23 (passive bad_spell 36, 12-C 0.32, beaten 6, blind 0.29, ai 0.68) |
| SPAN25 PAST3 BUST1.5 LOSS0.4 | 0.23 | 0.50 | 0.54 | 0.52 | 0.22 | 0.67 | 0.24 | +0.31 | +0.05 | 5.3 | 1.70 | 73 | 7 | 24 |
| SPAN25 PAST3 BUST1.5 LOSS0.5 | 0.23 | 0.49 | 0.54 | 0.52 | 0.22 | 0.67 | 0.24 | +0.31 | +0.05 | 5.3 | 1.72 | 73 | 7 | 24 |
| SPAN25 PAST3 BUST1.5 FADE0.25 LOSS0.4 | 0.23 | 0.49 | 0.54 | 0.52 | 0.13 | 0.67 | 0.18 | +0.31 | +0.05 | 5.3 | 1.71 | 72 | 7 | 23 |
| **SPAN30 PAST3 BUST1.5 FADE0.25** | 0.24 | 0.49 | 0.48 | 0.41 | **0.02** | 0.61 | 0.11 | +0.24 | -0.01 | 6.0 | 1.58 | 63 | 10 | **26** (bad_spell 35.6, pan12 6.01, blind 0.18, ai 0.61) |
| SPAN30 PAST3 BUST1.5 LOSS0.4 | 0.23 | 0.48 | 0.47 | 0.40 | 0.12 | 0.60 | 0.18 | +0.24 | -0.01 | 6.0 | 1.58 | 65 | 11 | 25 |
| SPAN30 PAST3 BUST1.5 LOSS0.5 | 0.23 | 0.48 | 0.47 | 0.40 | 0.11 | 0.60 | 0.18 | +0.24 | -0.01 | 6.0 | 1.58 | 65 | 11 | 25 |
| SPAN30 PAST3 BUST1.5 FADE0.25 LOSS0.4 | 0.23 | 0.48 | 0.47 | 0.40 | 0.02 | 0.60 | 0.11 | +0.24 | -0.01 | 6.0 | 1.58 | 64 | 11 | 26 |
| SPAN25 PAST3 BUST1.75 FADE0.25 | 0.23 | 0.48 | 0.52 | 0.50 | 0.10 | 0.66 | 0.16 | +0.29 | +0.04 | 5.7 | 1.67 | 71 | 7 | 23 |
| SPAN25 PAST3 BUST1.75 LOSS0.4 | 0.23 | 0.48 | 0.52 | 0.49 | 0.19 | 0.65 | 0.23 | +0.28 | +0.04 | 5.7 | 1.68 | 71 | 8 | 24 |
| SPAN25 PAST3 BUST1.75 LOSS0.5 | 0.23 | 0.47 | 0.51 | 0.48 | 0.19 | 0.65 | 0.23 | +0.28 | +0.04 | 5.7 | 1.66 | 71 | 9 | 24 |
| SPAN25 PAST3 BUST1.75 FADE0.25 LOSS0.4 | 0.23 | 0.48 | 0.52 | 0.48 | 0.09 | 0.65 | 0.16 | +0.28 | +0.04 | 5.7 | 1.68 | 71 | 8 | 23 |

What scan 2 shows:
- LEV_CRUNCH_FADE 0.25 (slower Bad Debts clearing) is what bites reckless play. LEV_RECORD_LOSS barely matters.
- The cost of FADE 0.25 is the passive "bad spell" miss, about 36 months against a target of at most 30.
- SPAN 25 keeps run12 ahead of hold6 (+0.04 to +0.05). SPAN 30 makes run12 tie or trail hold6 (-0.01) but punishes reckless more.

### Scan 3: IN FLIGHT AT DEATH (13:12:21, `g3.json`, 1,000 economies, seeds 1, 2, 3, no result recorded)
Candidates, each on top of 3/6/9/12 and the beta.4 values:
1. `{"LEV_PANIC_SPAN":30,"LEV_RECORD_PAST":3,"LEV_INCOME_FLOOR":0.005,"LEV_CRUNCH_FADE":0.3}`
2. `{"LEV_PANIC_SPAN":30,"LEV_RECORD_PAST":3,"LEV_INCOME_FLOOR":0.005,"LEV_CRUNCH_FADE":0.35,"LEV_CRUNCH_BUILD":0.05}` (the CRUNCH_BUILD 0.05 is already the base value)
3. `{"LEV_PANIC_SPAN":30,"LEV_RECORD_PAST":4,"LEV_INCOME_FLOOR":0.005,"LEV_CRUNCH_FADE":0.3}`
4. `{"LEV_PANIC_SPAN":30,"LEV_RECORD_PAST":3,"LEV_INCOME_FLOOR":0.004,"LEV_CRUNCH_FADE":0.3}`

**Intent (inferred):** keep SPAN 30's bite on reckless play, use a fade between 0.25 and 0.35 to avoid the bad-spell miss, and recover run12's lead over hold6 with more reward past 6 (PAST 4) or a lower income floor (0.004). BUST_PER_HYPE stays at the base 1.5.

To resume, rerun on the desktop:
```
$s='C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad'
cd G:\GameDev\speculative-markets
foreach($k in 1,2,3){ "seed $k"; py -3 -B $s\r12b.py 1000 $k $s\g3.json; py -3 -B $s\mania12.py one 1000 $k $s\g3.json | ? { $_ -match '/30' -and $_ -match '\{' } | % { $_.Substring([Math]::Max(0,$_.IndexOf('/30')-3)) } }
```
(`replay` step 080.) Then also check High volatility, as was done for beta.4:
```
$env:HV='78,0.25,1'; py -3 -B $s\mania12_h.py one 600 1 $s\l0.json
```

**Next steps the session had planned** (inferred from the 12:58 message and earlier patterns):
1. Pick a 3/6/9/12 candidate with run12 > hold6, reckless clearly below careful, and run12 panics ≤ about 5.5.
2. Confirm on three seeds and under High volatility.
3. Write the values into tuning.json.
4. Regenerate `build_scratch\rc_1.3.1` with `SPEC_MOD_OUT`, then run check.py and engine.py self-check.
5. Check the leverage bar for the new 6 and 9 steps. 3/10/11/12 gave narrow last steps, and it was never seen in game.
6. Write `beta\changelog_1.3.1-beta.5.bbcode`, stating old → new against **beta.3** (the live beta), not beta.4.
7. Build `beta/build.py --source build_scratch\rc_1.3.1 --out beta\release_131 --revision 5`, then stage_workshop and sync_live.
8. Ask before uploading.

The 12:58 message proposed building as **beta.5 and leaving the beta.4 package unpublished**. The user never explicitly answered that; they replied with the 3/6/9/12 instruction instead.

---

## 6. Files created or modified since 25020bb (uncommitted, on the desktop)

### Generators and tools (`G:\GameDev\speculative-markets\tools`)
- `tuning.json`: values per section 3. Current state is beta.4 plus LEV_LADDER [3,6,9,12]. It is now written with `json.dumps(indent=2)` and LF line endings.
- `generate.py`:
  - VERSION 1.3.1.
  - CREDIT_RUNOFF_TIGHT, `spec_credit_payoff` and `spec_credit_runoff_pct` script values, and the runoff `min = spec_credit_payoff` under Tight.
  - Tight-credit description text.
  - Heightened volatility {"heat": 78, "per": 0.25, "boom": 1} plus comment and rule text ("overheat sooner").
  - AI stance block replaced by `{credit_ai.STANCE}`.
  - `STANCE_CREDIT = {"tight": 0, "loose": tuning.get("LOOSE_CREDIT", 1.6)}`.
- `credit_ai.py`: margin-based AI rule (AI_MARGIN*, `spec_ai_margin`, `spec_ai_loose_lev`, `STANCE`). AI_TIGHT was removed.
- `leverage.py`:
  - AI limit default 6.5/8/9.5. AI_LEV_BACK, AI_EXIT_TIGHT and AI_BACK were removed.
  - `spec_lev_record_gap`; RECORD_FROM/RECORD_PAST (Sound Credit counts each month past 6 as 1 + PAST).
  - Sound Credit description: "+1.7% … and +5% for each month past 6".
  - RECORD_FADE was added and then removed.
- `market_tab.py`: tooltips for runoff % and the Tight stance.
- `concepts.py`: Outstanding Credit text ("…and much more under Tight").
- `values_table.py`: AI row now "AI turns Tight within 10 of a panic".
- `tuner.py`: added CREDIT_RUNOFF_TIGHT. AI_TIGHT replaced by AI_MARGIN.
- `fastsim.py`: `credit_ai.AI_TIGHT` replaced by the literal 80.

### Simulator (`tools\tuner\`)
- `engine.py`:
  - CREDIT_RUNOFF_TIGHT payoff capped by the pool.
  - AI margin rule.
  - Plan bots cut4, hold6, run10, blind10, run12, blind12.
  - Metrics growth_core, lev8_pct, runs10_per_century, runs10_out_pct, beaten_pct; run12's run-up threshold is 11.3.
  - LEV_RECORD_PAST.
  - Construction clamped ≥ -1.
  - PRICE_SPREAD 0.75, PRICE_COMMON 0.4.
- `inputs.json`: refit roughness and price_sd.
- `lab.py`: beaten_pct hook.
- `server.py`: drops `_core` from summary.
- `targets.json`: replaced at 00:20 with a 30-row ladder set. At 12:23 run10 became run12 and blind10 became blind12, with the text changed to "up to 12 months".

### Beta and packaging (`beta\`)
- `changelog_1.3.1-beta.1.bbcode`, `-beta.2`, `-beta.3`, `-beta.4` (all new).
- `workshop_description.bbcode`: now names beta.4 and says "running leverage up to 12 months pays…". Note that the live Workshop description was last uploaded with beta.3.
- `beta\release_131\mod\` plus `releases\Speculative_Markets_Beta_1.3.1-beta.{1,2,3,4}.zip` and manifests:

| Package | sha256 | Status |
|---|---|---|
| beta.1 | `ECB486F511167A47B5D6D318B169E46AA7A29CC09E76D721E6469B44E342F334` | never uploaded |
| beta.2 | `847630FB21E826278D3E7E4D0D3053D8DFAEE3BB0CE579A3BFAF45ABDBC7F124` | uploaded 02:01 |
| beta.3 | `DF2D2A4566FA55E0615C735A7CC08503C051DBA80D0371A7DDBE7420294A2921` | uploaded 06:03, **current live Beta** |
| beta.4 | `0B9701668D4CE009C73B3026CB6CFCA4D7872F09DC98159DB46F16FA72EA899E` | built and staged, **NOT uploaded** |

Other packaging state:
- `workshop\upload_staging\beta` is **currently staged with beta.4**. Running `steam_upload.py update beta --execute` would upload beta.4. Restage before uploading anything else.
- Upload receipts are in `workshop\upload_receipts\` (beta.2 02:01, beta.3 `20261125T0602xx`).
- In `build_scratch\`:
  - `rc_1.3.1` is the generated beta.4 build. It includes a thumbnail copy.
  - `rivals_live` is the dev folder, synced to beta.4.
  - `candidate_131_nothumb` holds an old candidate.
  - `built_against_rc_1.3.1.txt` was moved out of the build so packaging works. For beta.4 it was moved into the scratchpad as `built_against_b4.txt`.
  - `beta3_test\` holds the headless test user directory.
- `runs\sweep_beta3\beta3_01\` holds the beta.3 game logs, used for calibration.

### Unchanged
`mod\` (stable 1.3.0). Compatibility patches were not rebuilt: Morgenroete, TechRes and BPM are still built for 1.3, and the beta notes tell testers to run without them.

### Outside the repo
- Memory: `C:\Users\rwdav\.claude\projects\G--GameDev-speculative-markets\memory\leverage-ladder-targets.md`, created 00:25 and rewritten 11:47 with the "run up to 12" correction, plus a `MEMORY.md` index line.
- Scratch: `_claude_scratch\v130\` (infographic, infographic131, ridesim, waterworks.html, wwtest) and `_claude_scratch\tune_fresh\`.

---

## 7. Release / external state

| Item | Version / state |
|---|---|
| Stable Workshop | 1.3.0, uploaded and confirmed public before the commit. Git commit 25020bb is pushed. |
| Beta Workshop (item 3839275304) | **1.3.1-beta.3**, uploaded 2026-11-25 06:03 with update_verified. Its change notes overstate Mania (they quote the old simulator: about 8% hands-off and 5% AI). The beta.4 notes include the correction; a posted note can only be edited on the Workshop page. |
| beta.4 | Built and staged, not uploaded. Probably superseded by beta.5 with 3/6/9/12 (not confirmed by the user). |
| Morgenroete 1.3.0, TechRes 1.2.0, BPM 1.1.0, CMF | Unchanged since the 1.3 publish |
| Tutorial artifact | https://claude.ai/artifact/RK4Lrf6U1rU7HC8Vx5pDvy, version 12, describes **1.3 stable**. It was deliberately not updated for the betas. |
| Infographic "Does the Market Pay?" | `_claude_scratch\v130\infographic\does_it_pay.png`: 1.3 numbers, "Balanced" label, Mania icon for Reckless. Never posted; the user was asked to upload it to imgur and send the link, then told to hold off (20:50). `infographic131\does_it_pay.png` is a beta.1-numbers draft and is out of date. |
| Stable Workshop description | Still shows the 1.2.1 AI chart. It was waiting on the imgur link, now on hold. |

AGENTS.md compliance:
- No real-game test exists for beta.4 or later. The only real-game check is the beta.3 AI-only 1836–1866 headless run: clean load, no new mod errors.
- `quick_test.py --engine` was not run in this period, as far as the transcript shows (*uncertain*).
- Mechanics-audit checks and the Finance navigation UI were not exercised.

---

## 8. Pending items and open questions for the user

1. **3/6/9/12 retune**: finish scan 3 or redo it, choose values, and confirm on seeds plus High volatility.
2. **Build beta.5** with 3/6/9/12 (recommended), or upload the existing beta.4 (3/10/11/12). The user had not answered "Shall I upload beta.4?". Their 3/6/9/12 message implies beta.4 should not go out as is.
3. **beta.3 change notes** overstate Mania. The user can edit them on the Workshop page, or the next beta's notes can correct them (the beta.4 notes already do).
4. **Known misses at beta.4** (expect similar on 3/6/9/12):
   - AI growth about 0.65 (target ≤ 0.5); AI rivals may feel too strong.
   - run12 panics about 6 (≤ 5.5).
   - blind12 pays too well.
   - Passive growth about 0.2.
   - hold6 roughly ties run12.
   - Under High volatility, hold6 edges ahead.
5. **Not done**:
   - Real-game test of beta.4 or later. Run-up feel, the leverage bar layout and Mania after 1866 are all unchecked.
   - Translations of new 1.3.1 text (English only).
   - Patch rebuilds (Morgenroete, TechRes, BPM) for 1.3.1.
   - Commit of 1.3.1 work.
   - Infographic and tutorial update, on hold until balance settles.
   - Stable Workshop chart swap, waiting on imgur.
6. **Unanswered user status pings** at 11:57 and 12:13 got no text reply. The next session should give a status first.
7. **Claims later corrected by the session itself:**
   - "riding beats everyone" in beta.1 was wrong.
   - "AI panics less than 1.3" did not hold in the real game.
   - The beta.3 Mania figures were too high.
   - "Sound Credit's fade was the real problem" was wrong.
   - The 3/10/11/12 ladder was called a mistake.

---

## 9. Things to watch when resuming

- Treat beta.4 as **not uploaded**. The live beta is beta.3.
- Workshop staging holds beta.4. Restage before any upload.
- Do not describe a package as published unless Steam's update_verified is observed (AGENTS.md).
- tuning.json on the desktop diverges from every built package, because of the ladder [3,6,9,12].
- `lab.py check KEY=v` may print the better of old and new under the new label. Use `latest.json` or the scratch scripts.
- The PowerShell `py -c "…\"…\"…"` quoting failed silently once (step 780). Prefer script files.
- Commands over 10 minutes must run in the background. Use the "spawn" multiprocessing guard and `OMP_NUM_THREADS=1`.
