# paint one icon slot with Codex: ./paint.sh <name>
cd "$(dirname "$0")"
name=$1
read -r desc refs <<<"$(py -3 -c "
import sys; sys.path.insert(0, '../tools'); import icons
n='$name'; d=icons.SLOTS[n][2] + (icons.LAW_EMBLEM if n.startswith('law_') else '')
r={'state':'refs/investment_banks.png refs/central_banking.png raw/state_steady.png','mod':'refs/modifier_coins_negative.png refs/modifier_coins_positive.png',
   'je':'refs/event_trade.png refs/event_protest.png','event':'refs/event_trade.png refs/event_protest.png','crash':'refs/warning.png refs/investment_banks.png',
   'mapmode':'refs/mapmode_market_areas.png refs/investment_banks.png','driver':'refs/investment_banks.png raw/state_steady.png','lever':'refs/investment_banks.png refs/modifier_coins_negative.png','interest':'refs/investment_banks.png raw/driver_drift.png raw/driver_boom.png','ending':'refs/acceptance_tier3.png raw/driver_crash.png raw/crash_risk.png','blue':'refs/acceptance_tier3.png refs/investment_banks.png raw/name_companies.png','concept':'refs/investment_banks.png refs/central_banking.png raw/state_steady.png','law':'refs/law_laissez_faire.png refs/law_interventionism.png','principle':'refs/principle_advanced_research.png refs/principle_companies.png'}[n.split('_')[0]]
print(d.replace(' ', '_'), r)")"
desc=${desc//_/ }
out="raw/$name.png"
[[ $name == law_* ]] && out="raw/emblem/$name.png"  # law_metal (tools/) gives it vanilla's metal at build time
[ -f "$out" ] && { echo "skip $name"; exit 0; }

# Codex's sandbox can be read-only, so the image is collected from ~/.codex/generated_images/<session id>, where
# the image tool saves it either way. codex <log> <out> <prompt> <images...>
codex_image() {
  local log=$1 out=$2 prompt=$3; shift 3
  timeout 1200 codex exec --skip-git-repo-check -s workspace-write -C . "$prompt Transparent background. Generate exactly one image and do not edit files." -i "$@" < /dev/null > "$log" 2>&1
  local sid img
  sid=$(grep -m1 -o 'session id: [0-9a-f-]*' "$log" | cut -d' ' -f3)
  img=$(ls -t ~/.codex/generated_images/"$sid"/*.png 2>/dev/null | head -1)
  [ -n "$img" ] && cp "$img" "$out"
}

if [[ $name == law_* ]]; then
  # vanilla's law icons are flat emblems in one painted metal: Codex draws only the emblem
  mkdir -p raw/emblem
  codex_image "log_$name.txt" "$out" \
    "Using your image generation tool, create ONE flat Victoria 3 law emblem matching the attached law icons: $desc." $refs
else
  style=$(tr '\n' ' ' < style.md)
  codex_image "log_$name.txt" "$out" "Style guide: $style Using your image generation tool, create ONE icon in exactly that style, matching the attached Victoria 3 icons in rendering, lighting and palette: $desc." $refs
fi
[ -f "$out" ] && echo "done $name" || echo "FAILED $name"
