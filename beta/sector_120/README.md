# Market sectors in 1.2.0-beta.17

Every tracked good contributes its turnover to one sector. Finance uses the completed review for the selected good. A sector can dampen the price component of Investor Interest by 0–50%. A flat good has no price pressure. A newly initialized sector uses the good’s own price trend until it has a previous reading.

| Market sector | Base goods | Tech & Res additions |
| --- | --- | --- |
| Food & Provisions | grain, fish, meat, fruit, groceries, sugar | water |
| Plantation Trades | tea, coffee, tobacco, opium, wine, liquor | — |
| Textiles & Household Goods | fabric, silk, dye, clothes, luxury clothes, furniture, luxury furniture, porcelain, fine art | cosmetics, homeappliances, elgar instruments, manzoni prints, on demand goods |
| Timber, Metals & Materials | wood, hardwood, iron, copper, lead, steel, glass, paper | advancedores, alloys, aluminium, bauxite, commonores, rare earths |
| Fuel & Power | coal, oil, electricity | gas, global electricity, good uranium, heavy fuel, light fuel, lubricant, batteries |
| Machinery & Chemicals | tools, engines, rubber, sulfur, fertilizer, explosives | plastics, pharmaceuticals, robotics |
| Transport & Shipping | clippers, steamers, merchant marine, automobiles | civil planes, space assets |
| Arms & Ordnance | small arms, artillery, ammunition, tanks, aeroplanes | — |
| Electronics & Communications | telephones, radios | ai systems, business data, computer, copperwires, electroniccomponents, interactive entertainment, organized data, processors, raw data, softwares, telecommunications, televisions |

The base and compatibility generators passed their static checks. All 49 base and 85 extended goods have one verified sector assignment and a Finance receipt. The Python, generated-mod and CMF quick checks passed. All ten translations generated without English fallback. This build awaits native tooltip, bulletin and campaign verification. Beta.16 is the last build with a completed native campaign.

Tech & Res archive SHA-256: `8013b27a6623b5254825e8d74ed9f75526fbb76823088b5ddf0eec04cfd99fcb`.
