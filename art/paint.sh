# paint one icon slot with Codex: ./paint.sh <name>
cd "$(dirname "$0")"
name=$1
read -r desc refs <<<"$(py -3 -c "
import sys; sys.path.insert(0, '../tools'); import icons
n='$name'; d=icons.SLOTS[n][2]
r={'state':'refs/investment_banks.png refs/central_banking.png raw/state_steady.png','mod':'refs/modifier_coins_negative.png refs/modifier_coins_positive.png',
   'je':'refs/event_trade.png refs/event_protest.png','event':'refs/event_trade.png refs/event_protest.png','crash':'refs/warning.png refs/investment_banks.png',
   'mapmode':'refs/mapmode_market_areas.png refs/investment_banks.png','driver':'refs/investment_banks.png raw/state_steady.png','lever':'refs/investment_banks.png refs/modifier_coins_negative.png','interest':'refs/investment_banks.png raw/driver_drift.png raw/driver_boom.png','ending':'refs/acceptance_tier3.png raw/driver_crash.png raw/crash_risk.png','blue':'refs/acceptance_tier3.png refs/investment_banks.png raw/name_companies.png'}[n.split('_')[0]]
print(d.replace(' ', '_'), r)")"
desc=${desc//_/ }
[ -f "raw/$name.png" ] && { echo "skip $name"; exit 0; }
timeout 1200 codex exec --skip-git-repo-check -s workspace-write -C . "Read style.md. Using your image generation tool, create ONE icon in exactly that style, matching the attached Victoria 3 icons in rendering, lighting and palette: $desc. Transparent background. Save the final PNG as raw/$name.png in this directory. Do not create any other files. Reply with only the saved path." -i $refs < /dev/null > "log_$name.txt" 2>&1
[ -f "raw/$name.png" ] && echo "done $name" || echo "FAILED $name"
