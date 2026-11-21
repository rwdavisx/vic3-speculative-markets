# Finance sectors in 1.2.0-beta.22

Investor Interest shows sector turnover as a native box chart. Each rectangle is sized by the sector's share of the last completed monthly review. Sector headers show that percentage. The header, filter and chart tooltips list the sector's goods, the turnover share and the price trend used in the previous sector comparison.

Sector filters use the game's round goods buttons and the same ring states as the interest-tier filters. With all goods visible, every sector has a ring. Selecting one keeps its icon bright and its ring visible. Clicking it again restores all goods.

## Verification

The 235-file base package passed the Python, generated-mod and CMF quick checks. The targeted Finance tests exercise all nine ring selections, the icon in both button states, the native box chart and membership in the header tooltips. All ten base languages have 3,167 current translated entries. The five rebuilt CMF GUI files match beta.20 byte for byte.

The player preview profile points to this package for its next launch. Live rendering and the native engine gate are pending. To inspect, advance through the first monthly review and open Finance → Speculation → Investor Interest. Check the Food & Provisions chart rectangle and header for the same share. Select the wheat icon twice to inspect its selected state and restore the list.

Base archive SHA-256 `e6115d22fab06d9b83dcb9a117a0ab28f2e7d50dd8812a11df2f96a7e1e46a0c`.

TechRes SHA-256 `a0317b8556dab4a1a1920ea73a474399d1597f445f01d4bbd38506686a91d4a1`.

CMF SHA-256 `d18a45818e00baa85c5195aee518fc132f9bda6eca0083d60b98c38dbfacc8e9`.
