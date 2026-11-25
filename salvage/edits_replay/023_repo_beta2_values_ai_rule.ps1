cd G:\GameDev\speculative-markets
$p="C:\Users\rwdav\AppData\Local\Temp\claude\9dc80ff708ec737b\9c1684c5-3088-47d7-b848-def38336bbe9\scratchpad\beta2.py"
@'
import re, json
from pathlib import Path
R=Path(r'G:\GameDev\speculative-markets\tools')
def ed(f, *pairs):
    p=R/f; s=p.read_bytes().decode('utf-8'); nl='\r\n' if '\r\n' in s else '\n'; s=s.replace('\r\n','\n')
    for a,b in pairs:
        assert s.count(a)==1,(f,s.count(a),a[:90]); s=s.replace(a,b)
    p.write_bytes(s.replace('\n',nl).encode('utf-8'))
# values
ed('tuning.json',('"FIN_BOOM_BASE": 1.5','"FIN_BOOM_BASE": 1.75'),('"LEV_PANIC_SPAN": 50','"LEV_PANIC_SPAN": 35'),('"LEV_INCOME_FLOOR": 0.009','"LEV_INCOME_FLOOR": 0.007'),
   ('"LEV_RECORD_GAIN": 0.01','"LEV_RECORD_GAIN": 0.02'),('"LEV_CRUNCH_BUILD": 0.05','"LEV_CRUNCH_BUILD": 0.06'))
ed('generate.py',('"heightened": {"heat": 70, "per": 0.25, "boom": 1.1}','"heightened": {"heat": 75, "per": 0.25, "boom": 1}'),
 ('"Speculative booms will grow larger and end more abruptly, and "','"Speculative booms will overheat sooner and end more abruptly, and "') if '"Speculative booms will grow larger and end more abruptly, and "' in (R/'generate.py').read_text(encoding='utf-8') else ('Speculative booms will grow larger and end more abruptly, and ','Speculative booms will overheat sooner and end more abruptly, and '),
 ('# 0.25 x heat, booms x1.25), which gave the 40 largest economies 6.1 panics per 100 country years to history\'s 4\n','# 0.25 x heat, booms x1.25), which gave the 40 largest economies 6.1 panics per 100 country years to history\'s 4.\n# 1.3.1: heat 70 -> 75, booms 1.1 -> 1, as the base boom size grew\n'))
g=(R/'generate.py').read_bytes().decode('utf-8'); crlf='\r\n' in g; g=g.replace('\r\n','\n')
i=g.index('\t\t\t\tif = {{\n\t\t\t\t\tlimit = {{\n\t\t\t\t\t\t{leverage.ai_tight("var:spec_conf > spec_ai_tight_at")}')
j=g.index('\t\t\t\tif = {{\n\t\t\t\t\tlimit = {{\n\t\t\t\t\t\tspec_can_rescue = yes',i)
g=g[:i]+'{credit_ai.STANCE}'+g[j:]
g=g.replace('# AI countries use the same tools by rule: cool a mania, stop cooling once it has passed,\n\t\t\t# loosen when wary, and stop loosening once confidence is back','# AI countries use the same tools by rule: borrow while a panic is far off, and pay loans off as it nears')
(R/'generate.py').write_bytes((g.replace('\n','\r\n') if crlf else g).encode('utf-8'))
# the AI rule
ed('credit_ai.py',
('''# a Balanced AI tightens above this, at the Mania line: it answers a mania rather than heading it off, as the
# century's banks did. 76 (before the line) had the AI Tight 11 to 12% of months by the 1890s and Mania under 2%
AI_TIGHT = tuning.get("AI_TIGHT", 80)
''','''# the AI's credit rule (1.3.1) watches its margin: confidence over the Panic Threshold, plus AI_MARGIN_LEAN of its lean.
# From AI_MARGIN_FROM months of leverage it goes Tight under AI_MARGIN and stays so until AI_MARGIN_BACK. It goes Loose
# over AI_MARGIN_LOOSE, while it is AI_LOOSE_ROOM months or more short of its leverage limit (leverage.AI_LIMIT)
AI_MARGIN, AI_MARGIN_BACK, AI_MARGIN_LOOSE = tuning.get("AI_MARGIN", 10), tuning.get("AI_MARGIN_BACK", 16), tuning.get("AI_MARGIN_LOOSE", 15)
AI_MARGIN_FROM, AI_MARGIN_LEAN, AI_LOOSE_ROOM = tuning.get("AI_MARGIN_FROM", 4), tuning.get("AI_MARGIN_LEAN", 0.6), tuning.get("AI_LOOSE_ROOM", 0.5)
'''),
('''    # a positive lean means the AI tightens later, loosens sooner and stays loose longer
    at = {"tight": AI_TIGHT, "untight": AI_TIGHT - 1, "loose": tuning.get("AI_LOOSE", k["WARY"]), "unloose": k["CREDIT_FROM"]}
    # confidence drifts to CONF_START, so the way back to Normal must lie on its far side or a stance can stick:
    # leave Tight below at least CONF_START + 3, leave Loose from at most CONF_START - 1 (still above the highest
    # loosen point, WARY + TEMPER_SHIFT + IG_SHIFT = 52, so the AI does not flip back and forth)
    clamp = {"untight": f"\\tmin = {k['CONF_START'] + 3}\\n", "unloose": f"\\tmax = {k['CONF_START'] - 1}\\n"}
    # the lowest tighten point stays above the untight floor, so a Cautious AI cannot tighten and loosen in turn
    assert AI_TIGHT - TEMPER_SHIFT - IG_SHIFT > k["CONF_START"] + 3, "the lowest tighten point must stay above the untight floor"
''','''    # when the AI starts and stops encouraging Calm goods (levers.py): it stops from at most CONF_START - 1, above the
    # highest starting point, WARY + TEMPER_SHIFT + IG_SHIFT
    at = {"loose": tuning.get("AI_LOOSE", k["WARY"]), "unloose": k["CREDIT_FROM"]}
    clamp = {"unloose": f"\\tmax = {k['CONF_START'] - 1}\\n"}
    assert AI_MARGIN < AI_MARGIN_BACK, "the AI would tighten and loosen in turn"
'''),
('''{clamp.get(n, '')}}}" for n, v in at.items()]
''','''{clamp.get(n, '')}}}" for n, v in at.items()]
    values += [f"spec_ai_margin = {{\\n\\tvalue = spec_ai_lean\\n\\tmultiply = {AI_MARGIN_LEAN}\\n\\tadd = var:spec_conf\\n\\tsubtract = spec_panic_at\\n}}",
               f"spec_ai_loose_lev = {{\\n\\tvalue = spec_ai_lev_limit\\n\\tsubtract = {AI_LOOSE_ROOM}\\n}}"]
'''),
('''def ig_lines(stance):''','''# the AI's monthly choice of Credit Policy, for generate.monthly. A Mania fever (leverage.FEVER) keeps it from tightening
_EXIT = f"""spec_stance_value = -1
spec_lev < spec_ai_lev_limit
NOT = {{ has_variable = spec_crunch }}
OR = {{
	spec_lev < {AI_MARGIN_FROM}
	spec_ai_margin >= {AI_MARGIN_BACK}
}}"""
_LOOSE = f"""spec_ai_margin > {AI_MARGIN_LOOSE}
spec_lev < spec_ai_loose_lev
NOT = {{ has_variable = spec_panic }}"""


def _tabs(text, n):
    return "\\n".join("\\t" * n + line for line in text.split("\\n"))


def _choice(word, limit, stance):
    return f"\\t\\t\\t\\t{word} = {{\\n\\t\\t\\t\\t\\tlimit = {{\\n{_tabs(limit, 6)}\\n\\t\\t\\t\\t\\t\\tspec_can_stance_{stance} = yes\\n\\t\\t\\t\\t\\t}}\\n\\t\\t\\t\\t\\tspec_stance_to_{stance} = yes\\n\\t\\t\\t\\t}}\\n"


STANCE = (
    _choice("if", f"""OR = {{
	spec_lev >= spec_ai_lev_limit
	has_variable = spec_crunch
	AND = {{
		spec_lev >= {AI_MARGIN_FROM}
		spec_ai_margin < {AI_MARGIN}
	}}
}}
NOT = {{ has_variable = spec_ai_fever }}
NOT = {{ spec_stance_value = -1 }}""", "tight")
    + _choice("else_if", f"""OR = {{
	spec_stance_value = 0
	AND = {{
{_tabs(_EXIT, 2)}
	}}
}}
{_LOOSE}""", "loose")
    + _choice("else_if", _EXIT, "normal")
    + _choice("else_if", f"""spec_stance_value = 1
NOT = {{
	AND = {{
{_tabs(_LOOSE, 2)}
	}}
}}""", "normal"))


def ig_lines(stance):'''),
('''    assert f"spec_ai_untight_at = {{\\n\\tvalue = {AI_TIGHT - 1}\\n\\tadd = spec_ai_lean\\n\\tmin = 58\\n}}" in v and "\\tmax = 54\\n" in v
    assert f"spec_ai_tight_at = {{\\n\\tvalue = {AI_TIGHT}\\n\\tadd = spec_ai_lean\\n}}" in v
''','''    assert "\\tmax = 54\\n" in v and "spec_ai_margin = {" in v
    assert STANCE.count("{") == STANCE.count("}") and "{{" not in STANCE, "unbalanced STANCE"
'''))
ed('leverage.py',('{"-1": 5, "0": 8, "1": 9.5})  # Cautious was 3: a third of the AI never passed the safe line (tune12); Bold was 12, the ruin line','{"-1": 6.5, "0": 8, "1": 9.5})  # Cautious was 5 before 1.3.1; Bold was 12, the ruin line (tune12)'),
('# months of leverage at which the AI turns Tight, by temperament; it stays Tight until half that. A limit below this means only\n# falling income can set it off\n','# months of leverage at which the AI turns Tight, by temperament, however far off a panic is (credit_ai.STANCE)\n'),
('# the AI\'s tables, each moved as one by its scale (tuning.scaled), and the share of its limit it loosens back below\n','# the AI\'s tables, each moved as one by its scale (tuning.scaled)\n'),
('AI_LEV_BACK = tuning.get("AI_LEV_BACK", 0.5)\n',''),
('        f"spec_ai_lev_back = {{\\n\\tvalue = spec_ai_lev_limit\\n\\tmultiply = {AI_LEV_BACK}\\n}}",\n',''),
('AI_EXIT_TIGHT = "" if not ON else "\\t\\t\\t\\t\\t\\tspec_lev < spec_ai_lev_limit\\n"\nAI_BACK = "" if not ON else "\\t\\t\\t\\t\\t\\tspec_lev < spec_ai_lev_back\\n"\n',''))
s=(R/'leverage.py').read_bytes().decode('utf-8'); nl='\r\n' if '\r\n' in s else '\n'; s=s.replace('\r\n','\n')
a=s.index('# The AI tightens above its leverage limit and can return'); b=s.index('# when a Mania fires, and each month in the AI')
s=s[:a]+s[b:]; (R/'leverage.py').write_bytes(s.replace('\n',nl).encode('utf-8'))
ed('values_table.py',('It stays Tight until half that.','However far off a panic is.'),
 ('("AI cools at", f"{a.AI_TIGHT} confidence", "The AI turns Tight above this.", "a.AI_TIGHT")','("AI turns Tight within", f"{a.AI_MARGIN} of a panic", f"Confidence over the Panic Threshold, from {a.AI_MARGIN_FROM} months of leverage. Back from {a.AI_MARGIN_BACK}, Loose over {a.AI_MARGIN_LOOSE}.", "a.AI_MARGIN")'))
ed('tuner.py',('    ("AI_TIGHT", "AI", "AI tightens above", "A Balanced AI tightens credit above this confidence"),\n','    ("AI_MARGIN", "AI", "AI tightens within", "A Balanced AI tightens credit this close to a panic"),\n'))
s=(R/'fastsim.py').read_bytes().decode('utf-8').replace('credit_ai.AI_TIGHT','80'); (R/'fastsim.py').write_bytes(s.encode('utf-8'))
'@ | Set-Content -Encoding utf8 $p
py -3 -B $p
Select-String tools\*.py,tools\tuner\*.py -Pattern 'AI_TIGHT|AI_LEV_BACK|AI_EXIT_TIGHT|AI_BACK\b|ai_tight\(|lev_back|untight_at|spec_ai_tight' | % {"$($_.Filename):$($_.LineNumber): $($_.Line.Trim().Substring(0,[Math]::Min(150,$_.Line.Trim().Length)))"}
Select-String tools\generate.py -Pattern 'spec_can_stance_|import credit_ai|credit_ai' | select -First 14 | % {"$($_.LineNumber): $($_.Line.Trim().Substring(0,[Math]::Min(260,$_.Line.Trim().Length)))"}; git diff --stat
