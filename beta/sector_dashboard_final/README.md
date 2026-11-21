# Finance sector dashboard in 1.2.0-beta.20

Investor Interest groups goods by sector in all three sort modes. Select a sector icon to filter, then select it again to show all goods. The chart shows shares of tracked turnover in the last completed monthly review. Hover a good for its sector trend and the reduction to its price signal.

## Verification

The 235-file base beta matched its dev installation. Python, generated-mod and CMF quick checks passed. All ten localizations have current translations for 3,166 base entries and 3,866 extended entries. The Machinery & Chemicals icon was inspected at both display sizes. The rebuilt CMF GUI payload matches beta.18. The Tech & Res patch was rebuilt against beta.20 with 85 goods.

The nine-sector offline tuner met 18 of 18 targets on seeds 911, 1123 and 1301 with 500 economies per strategy per seed. The last native 1836–1900 campaign used beta.16. Beta.20 awaits its native engine gate and live Finance inspection. The candidate is unpublished.

## In-game spot check

Open Finance from the journal and from a good. Confirm the intended tab opens. After two monthly reviews, filter Investor Interest to Food & Provisions, inspect grain's trend and dampening tooltip, then click the filter again to restore all nine sectors. Check the turnover chart and row alignment in your usual window size. For CMF, also check the transition back to the native panel.

## Archive hashes

- Base SHA-256 — 2728d5838cf09aab37bfa4774b1db314c1d771b764b6151350dcdb79d7bfd5c7
- TechRes SHA-256 — `ee95e0671b2cbd9501d9b048963139eb19c42ebd420a19dc5505388c0a435054`
- CMF SHA-256 — `a9843c6b9027a8263e1255d8cccfe17d4ccb892a79cb09fcf5043b99bfe16e7d`
