# paint icon slots or event pictures with Codex, in parallel: ./paint.ps1 <name> [<name> ...]   (PowerShell twin of paint.sh)
param([Parameter(Mandatory)][string[]]$Names, [string]$Model)
Set-Location $PSScriptRoot
$refs = @{ excess = 'refs/alert_expensive_goods.png refs/alert_market_over_capacity.png raw/crash_risk.png'
           rival = 'refs/investment_banks.png refs/rivalry.png raw/name_companies.png'
           name = 'raw/name_price.png raw/name_harbour.png raw/name_companies.png'
           so = 'refs/investment_charter.png refs/gdp.png refs/basic_construction.png refs/trade.png'
           picture ='refs/event_trade.png refs/investment_banks.png' }
$jobs = foreach ($n in $Names) {
    if (Test-Path "raw/$n.png") { "skip $n"; continue }
    $desc = py -3 -c "import sys; sys.path.insert(0, '../tools'); import icons; print(icons.PICTURES.get('$n') or icons.SLOTS['$n'][2])"
    if ($n -like 'picture_*') {
        $ask = "Read style.md for its palette and painterly rendering only. Using your image generation tool, create ONE Victoria 3 style event illustration: a full opaque painted scene, not an icon, no transparency, near-square (about 1240 by 1200), with the main subject in the left two thirds because the right edge fades out in game: $desc. No text, letters or numbers. Save the final PNG as raw/$n.png in this directory. Do not create any other files. Reply with only the saved path."
    } else {
        $ask = "Read style.md. Using your image generation tool, create ONE icon in exactly that style, matching the attached Victoria 3 icons in rendering, lighting and palette: $desc. Transparent background. Save the final PNG as raw/$n.png in this directory. Do not create any other files. Reply with only the saved path."
    }
    $r = $refs[$n.Split('_')[0]].Split(' ')
    Start-Job -Name $n -ScriptBlock {
        param($dir, $n, $ask, $r, $Model)
        Set-Location $dir
        $m = if ($Model) { @('-m', $Model) } else { @() }
        $null | codex exec @m --skip-git-repo-check -s workspace-write -C . $ask -i @r *> "log_$n.txt"
        if (Test-Path "raw/$n.png") { "done $n" } else { "FAILED $n" }
    } -ArgumentList $PSScriptRoot, $n, $ask, $r, $Model
}
$jobs | Where-Object { $_ -is [string] }
$jobs | Where-Object { $_ -isnot [string] } | Wait-Job -Timeout 1800 | Receive-Job
