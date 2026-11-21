# Investor Interest rankings in 1.2.0-beta.28

The player’s Speculation tab now opens the Investor Interest section with the journal’s three Favoured and two Shunned goods. The summary uses the existing monthly ranking. Each good has its name and icon and an individual Investor Interest tooltip. The label tooltips explain the ranking and its link to producer throughput.

The sector chart lists four named sectors plus any remainder. The January 1839 Russia autosave from the hot-update session contained 141 nonempty chart lists. All 49 lists with an Other entry contained four named sectors and the remainder. The other 92 lists contained four named sectors. The same save stored opium, tools and silk in the three favoured slots, and lead and porcelain in the shunned slots.

## Checks

The base archive matched its 235 packaged files. Python, generated-mod and CMF quick checks passed. A generation check verified the order, five named goods, hover targets and local-player scope. The running debug session received the two changed GUI files. A live visual inspection of the new summary and its hover text is pending. The debug log also recorded an unresolved empty goods key in an earlier sector-tooltip lookup before this summary was applied.

Base archive SHA-256 `5469171c1b6e8b850ba69661059cd7820be747f015c270f612f5bd96f133c796`.
