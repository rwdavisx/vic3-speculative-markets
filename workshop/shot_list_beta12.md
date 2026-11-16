# Gallery shots for beta.12

Same setup as the existing raw/ shots: 4K (3840x2160), UI scale 150%, English, Finance panel docked left.
- `full_*.png`: the whole 4K screen with the Finance panel open (make_cards rings the Finance button at 35,795).
- `ui_*.png`: the Finance panel alone, 840x1870, scrolled or stitched so the section fills it.
- `ev_*.png`: the whole 4K screen with the event window centered (make_cards crops 1040,500 to 2810,1700).

Crop boxes in `make_cards.py` CARDS are starting points; refit them once a shot exists.

## New cards

| File | Card | Show | Crop notes |
| --- | --- | --- | --- |
| `raw/full_rivals.png` | 13_rivals | Exchanges tab, scrolled to Rivalries: Rival Actions on Us with a running Bear Raid or Lure, then Exchanges We Rival with two or three rows. One Contest bar clearly off-center with chevrons. | Card uses (0,110)-(916,1225): header through the first rival rows. Also the dimmed backdrop. |
| `raw/ui_rivals.png` | 13_rivals | Panel only, scrolled to Exchanges We Rival / Exchanges Rivaling Us, action buttons visible, at least one framed (running or cooling down) and a shield after a name. | Card uses the lower half, (0,935)-(840,1870). |
| `raw/ui_bluechips.png` | 14_bluechips | Speculation tab, panel only, Companies section with two or more medal badges and the blue chip count in the header. | Card uses the top (0,0)-(840,1190); put the Companies section at the top. |
| `raw/ev_coty.png` | 14_bluechips | Company of the Year event (spec_bluechip.3) as a player, option tooltip shown if it fits. | Event window inside (1040,500)-(2810,1700), as ev_panic. |
| `raw/full_renown.png` | 15_renown | Trading Floor tab, Paths to Renown with place rewards on the leader flags; a charter that shows Futures Pit, Lender to Nations or Railway Mania. | Card uses (0,110)-(916,1225). Also the dimmed backdrop. |
| `raw/ui_renown.png` | 15_renown | Panel only, Specialities rows, including a locked path showing its effects, bars and tallies. | Card uses the lower half, (0,935)-(840,1870). |

Good save for all six: a mid-game great power (1850s or later) at International Standing or a World Centre, with rivals named and a few blue chips.

## Retakes: tab names changed

The tab bar now reads Trading Floor, Speculation, Banking, Exchanges. Every shot showing the old tab bar is out of date. Keep the file names; make_cards expects them.

| File | Tab now | Used by |
| --- | --- | --- |
| `raw/full_exchange.png` | Trading Floor | 01_finance, 02_exchange (backdrop and crop) |
| `raw/ui_exchange.png` | Trading Floor | 02_exchange |
| `raw/full_speculation.png` | Speculation | 03_speculation, default backdrop of every card |
| `raw/ui_speculation.png` | Speculation | 01_finance, 03_speculation, thumbnail |
| `raw/full_banking.png` | Banking | 04_banking |
| `raw/ui_banking.png` | Banking | 01_finance, 04_banking |
| `raw/full_rankings.png` | Exchanges, Leading Exchanges list with the rivalry buttons | 05_rankings |
| `raw/ui_rankings.png` | Exchanges | 01_finance, 05_rankings |

Retake the same scroll positions as the old shots so the existing crop boxes still fit. The live page's imgur images (the four tab pictures in description.bbcode) show the old tabs too.
