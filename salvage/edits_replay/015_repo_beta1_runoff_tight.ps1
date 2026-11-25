cd G:\GameDev\speculative-markets
function Set-Rep($p,$a,$b){$f="$pwd\$p";$s=[IO.File]::ReadAllText($f); $n=([regex]::Matches($s,[regex]::Escape($a))).Count; if($n -ne 1){"COUNT $n in $p : $($a.Substring(0,[Math]::Min(60,$a.Length)))";return}; [IO.File]::WriteAllText($f,$s.Replace($a,$b))}
Set-Rep 'tools\tuning.json' '"FIN_BOOM_BASE": 1.0' '"FIN_BOOM_BASE": 1.5'
Set-Rep 'tools\tuning.json' '"LEV_PANIC_SPAN": 55' '"LEV_PANIC_SPAN": 50'
Set-Rep 'tools\tuning.json' '  "CREDIT_RUNOFF": 0.0095,' "  `"CREDIT_RUNOFF`": 0.0095,`n  `"CREDIT_RUNOFF_TIGHT`": 0.1,"
Set-Rep 'tools\generate.py' 'CLAWBACK = tuning.get("CLAWBACK"' "CREDIT_RUNOFF_TIGHT = tuning.get(`"CREDIT_RUNOFF_TIGHT`", CREDIT_RUNOFF)  # and under Tight credit, as far as the pool can pay it`nCLAWBACK = tuning.get(`"CLAWBACK`""
Set-Rep 'tools\generate.py' 'multiply = {CREDIT_RUNOFF}\n\t\tmin = 0\n\t}}\n}}")' 'multiply = {CREDIT_RUNOFF}\n\t\tmin = 0\n\t\tif = {{\n\t\t\tlimit = {{ spec_stance_value = -1 }}\n\t\t\tmin = spec_credit_payoff\n\t\t}}\n\t}}\n}}")'
$g="$pwd\tools\generate.py"; $s=[IO.File]::ReadAllText($g)
$a='    sv.append("spec_credit_repay = {'; if(([regex]::Matches($s,[regex]::Escape($a))).Count -ne 1){'REPAY?'}
$new='    # Tight credit pays loans off faster, but only out of what the pool holds: it never writes a loan off' + "`n" +
'    sv.append(f"spec_credit_payoff = {{\n\tvalue = var:spec_debt\n\tmultiply = {CREDIT_RUNOFF_TIGHT}\n\tmax = investment_pool\n}}")' + "`n" +
'    # the share of the loans that is, in percent' + "`n" +
'    sv.append("spec_credit_runoff_pct = {\n\tvalue = 0\n\tif = {\n\t\tlimit = { has_variable = spec_debt var:spec_debt > 0 }\n\t\tvalue = spec_credit_runoff\n\t\tdivide = var:spec_debt\n\t\tmultiply = 100\n\t}\n}")' + "`n"
[IO.File]::WriteAllText($g,$s.Replace($a,$new+$a))
Set-Rep 'tools\market_tab.py' "repaid each month (#v {k['CREDIT_RUNOFF']:.0%}#!)" "repaid each month (#v [{sv('spec_credit_runoff_pct')}|1]%#!)"
Set-Rep 'tools\market_tab.py' "\\nBanks stop lending. Each month, #N {tight_pull:.0%}#! of our [concept_spec_market_confidence] above" "\\nBanks stop lending. Each month, up to #P {k['CREDIT_RUNOFF_TIGHT']:.0%}#! of our [concept_spec_outstanding_credit] is paid back instead of #v {k['CREDIT_RUNOFF'] * 100:.2g}%#!, and #N {tight_pull:.0%}#! of our [concept_spec_market_confidence] above"
Set-Rep 'tools\generate.py' 'spec_credit_tight_desc: "#N Banks stop lending#! into the [concept_investment_pool]\\n' 'spec_credit_tight_desc: "#N Banks stop lending#! into the [concept_investment_pool]\\n#P {CREDIT_RUNOFF_TIGHT:.0%}#! of our [concept_spec_outstanding_credit] is paid back each month, instead of #v {CREDIT_RUNOFF * 100:.2g}%#!\\n'
Set-Rep 'tools\generate.py' 'VERSION = "1.3.0"' 'VERSION = "1.3.1"'
Set-Rep 'tools\tuner\engine.py' '    ("CLAWBACK", g, "CLAWBACK", "Panic"' "    (`"CREDIT_RUNOFF_TIGHT`", g, `"CREDIT_RUNOFF_TIGHT`", `"Credit`", `"Runoff a month, Tight`"),`n    (`"CLAWBACK`", g, `"CLAWBACK`", `"Panic`""
Set-Rep 'tools\tuner\engine.py' 'runoff = np.maximum(self.debt * K["CREDIT_RUNOFF"], 0)' "runoff = np.maximum(self.debt * K[`"CREDIT_RUNOFF`"], 0)`n        runoff = np.where(self.stance == -1, np.maximum(runoff, np.minimum(self.debt * K[`"CREDIT_RUNOFF_TIGHT`"], self.pool)), runoff)"
Set-Rep 'tools\tuner\engine.py' '        "spec_credit_runoff": [f"multiply = {K[''CREDIT_RUNOFF'']}"],' ('        "spec_credit_runoff": [f"multiply = {K[''CREDIT_RUNOFF'']}", "min = spec_credit_payoff"],' + "`n" + '        "spec_credit_payoff": [f"multiply = {K[''CREDIT_RUNOFF_TIGHT'']}", "max = investment_pool"],')
Set-Rep 'tools\tuner.py' '    ("CREDIT_RUNOFF", "Credit", "Repayment", "Share of outstanding credit repaid each month"),' ("    (`"CREDIT_RUNOFF`", `"Credit`", `"Repayment`", `"Share of outstanding credit repaid each month`"),`n    (`"CREDIT_RUNOFF_TIGHT`", `"Credit`", `"Repayment, Tight`", `"Share of outstanding credit repaid each month under Tight credit`"),")
Select-String tools\market_tab.py -Pattern "k\['CREDIT_RUNOFF|'CREDIT_RUNOFF'|CREDIT_RUNOFF=" | % {"$($_.LineNumber): $($_.Line.Trim().Substring(0,120))"}
Select-String tools\generate.py -Pattern 'STANCE_HYPE=|"STANCE_HYPE"|CREDIT_RUNOFF' | % {"$($_.LineNumber): $($_.Line.Trim().Substring(0,[Math]::Min(170,$_.Line.Trim().Length)))"}
$env:SPEC_MOD_OUT="$pwd\build_scratch\rc_1.3.1"; py -3 -B tools/generate.py 2>&1 | Select-Object -Last 4; py -3 -B tools/check.py 2>&1 | Select-Object -Last 4; py -3 -B tools/generate.py --help 2>&1 | Select-Object -First 0
Select-String build_scratch\rc_1.3.1\common\script_values\spec_values.txt -Pattern '^spec_credit_(runoff|payoff|runoff_pct) = ' -Context 0,14 | Out-String
